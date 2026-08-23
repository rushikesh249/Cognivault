import time
import httpx
import pytest

from backend.app.models.exceptions import ModelUnavailable, ProviderUnavailable
from backend.app.models.ollama_adapter import OllamaAdapter
from backend.app.models.schema import ModelConfig, ModelStatus, ProviderStatus


def test_provider_unavailable_on_connection_error():
    # Transport that raises ConnectError
    transport = httpx.MockTransport(lambda req: httpx.Response(503))
    client = httpx.Client(transport=transport)
    adapter = OllamaAdapter(base_url="http://fake-host:11434", http_client=client, cache_ttl_s=0.0)

    assert adapter.is_provider_available() is False
    assert adapter.get_provider_status() == ProviderStatus.UNAVAILABLE
    assert adapter.is_model_available("any-model") is False


def test_model_status_evaluation_with_mock_provider():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "qwen2.5:7b-instruct-q4_K_M"},
                        {"name": "llava:7b:latest"},
                    ]
                },
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OllamaAdapter(http_client=client, cache_ttl_s=0.0)

    assert adapter.is_provider_available() is True
    assert adapter.get_provider_status() == ProviderStatus.AVAILABLE

    # Available model
    assert adapter.is_model_available("qwen2.5:7b-instruct-q4_K_M") is True
    assert adapter.is_model_available("ollama://qwen2.5:7b-instruct-q4_K_M") is True
    assert adapter.is_model_available("llava:7b") is True

    # Unavailable model
    assert adapter.is_model_available("nonexistent-model:latest") is False

    # Model status evaluations
    model_avail = ModelConfig(
        model_id="gen-1",
        role="general",
        model_path="ollama://qwen2.5:7b-instruct-q4_K_M",
        enabled=True,
    )
    assert adapter.get_model_status(model_avail) == ModelStatus.AVAILABLE

    model_unavail = ModelConfig(
        model_id="code-1",
        role="coding",
        model_path="ollama://qwen2.5-coder:7b",
        enabled=True,
    )
    assert adapter.get_model_status(model_unavail) == ModelStatus.CONFIGURED

    model_disabled = ModelConfig(
        model_id="dis-1",
        role="general",
        model_path="ollama://qwen2.5:7b-instruct-q4_K_M",
        enabled=False,
    )
    assert adapter.get_model_status(model_disabled) == ModelStatus.UNAVAILABLE


def test_probe_caching():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"models": [{"name": "test-model"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OllamaAdapter(http_client=client, cache_ttl_s=10.0)

    adapter.is_provider_available()
    adapter.is_provider_available()
    adapter.is_model_available("test-model")
    
    # 3 calls made rapidly within cache TTL should hit the server only once
    assert call_count == 1


def test_ensure_loaded_and_lru_unload():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "model-a"}, {"name": "model-b"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OllamaAdapter(http_client=client, cache_ttl_s=0.0)

    assert adapter.ensure_loaded("model-a") is True
    assert adapter.ensure_loaded("model-b") is True

    # Unload LRU (should be model-a)
    assert adapter.unload_lru() is True
    # Unload next (should be model-b)
    assert adapter.unload_lru() is True
    # No more loaded models
    assert adapter.unload_lru() is False
