import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import httpx
import pytest
import yaml

from backend.app.api.models import get_model_adapter, get_model_registry
from backend.app.main import app
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.ollama_adapter import OllamaAdapter


def test_get_models_empty_registry():
    client = TestClient(app)
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)


def test_get_models_with_mocked_provider():
    test_data = {
        "models": [
            {
                "model_id": "test-gen-1",
                "display_name": "Test General",
                "role": "general",
                "capabilities": ["reasoning"],
                "modalities": ["text"],
                "context_length": 8192,
                "vram_gb": 5.5,
                "model_path": "ollama://qwen2.5:7b",
                "enabled": True,
            }
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(test_data, f)
        temp_path = Path(f.name)

    try:
        mock_registry = ModelRegistry(config_path=temp_path)

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}]})

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        mock_adapter = OllamaAdapter(http_client=mock_client, cache_ttl_s=0.0)

        # Override dependency injection
        app.dependency_overrides[get_model_registry] = lambda: mock_registry
        app.dependency_overrides[get_model_adapter] = lambda: mock_adapter

        client = TestClient(app)
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) == 1
        m = data["models"][0]
        assert m["model_id"] == "test-gen-1"
        assert m["role"] == "general"
        assert m["available"] is True
        assert m["status"] == "AVAILABLE"
        assert m["provider_status"] == "AVAILABLE"
    finally:
        app.dependency_overrides.clear()
        temp_path.unlink(missing_ok=True)
