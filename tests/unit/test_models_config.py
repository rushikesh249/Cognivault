import tempfile
from pathlib import Path
import pytest
import yaml

from backend.app.models.exceptions import ModelConfigurationError
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.schema import ModelConfig, ModelRegistryFile


def test_empty_registry():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump({"models": []}, f)
        temp_path = Path(f.name)

    try:
        registry = ModelRegistry(config_path=temp_path)
        assert registry.count() == 0
        assert registry.list() == []
        assert registry.get("nonexistent") is None
    finally:
        temp_path.unlink(missing_ok=True)


def test_valid_model_config_loading():
    valid_data = {
        "models": [
            {
                "model_id": "test-general-model",
                "display_name": "General Test Model",
                "role": "general",
                "capabilities": ["reasoning", "planning"],
                "modalities": ["text"],
                "context_length": 8192,
                "vram_gb": 5.5,
                "serving_backend": "ollama",
                "model_path": "ollama://qwen2.5:7b",
                "enabled": True,
            },
            {
                "model_id": "test-coding-model",
                "display_name": "Coding Test Model",
                "role": "coding",
                "capabilities": ["coding", "debugging"],
                "modalities": ["text"],
                "context_length": 16384,
                "vram_gb": 6.0,
                "serving_backend": "ollama",
                "model_path": "ollama://qwen2.5-coder:7b",
                "enabled": False,
            },
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(valid_data, f)
        temp_path = Path(f.name)

    try:
        registry = ModelRegistry(config_path=temp_path)
        assert registry.count() == 2
        
        # Test get by id
        m1 = registry.get_by_id("test-general-model")
        assert m1 is not None
        assert m1.role == "general"
        assert m1.capabilities == ["reasoning", "planning"]
        assert m1.context_length == 8192
        assert m1.enabled is True

        # Test get by role
        m_general = registry.get_by_role("general", enabled_only=True)
        assert len(m_general) == 1
        assert m_general[0].model_id == "test-general-model"

        # Test enabled_only filter for disabled model
        m_coding = registry.get_by_role("coding", enabled_only=True)
        assert len(m_coding) == 0
        m_coding_all = registry.get_by_role("coding", enabled_only=False)
        assert len(m_coding_all) == 1
        assert m_coding_all[0].model_id == "test-coding-model"
    finally:
        temp_path.unlink(missing_ok=True)


def test_duplicate_model_id_rejection():
    dup_data = {
        "models": [
            {
                "model_id": "duplicate-id",
                "role": "general",
                "capabilities": ["reasoning"],
                "modalities": ["text"],
                "context_length": 4096,
                "model_path": "ollama://model-a",
            },
            {
                "model_id": "duplicate-id",
                "role": "coding",
                "capabilities": ["coding"],
                "modalities": ["text"],
                "context_length": 8192,
                "model_path": "ollama://model-b",
            },
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(dup_data, f)
        temp_path = Path(f.name)

    try:
        with pytest.raises(ModelConfigurationError) as exc_info:
            ModelRegistry(config_path=temp_path)
        assert "Duplicate model_id" in str(exc_info.value)
    finally:
        temp_path.unlink(missing_ok=True)


def test_invalid_schema_rejection():
    invalid_data = {
        "models": [
            {
                "model_id": "",  # Empty model_id is invalid
                "role": "general",
                "model_path": "ollama://test",
            }
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(invalid_data, f)
        temp_path = Path(f.name)

    try:
        with pytest.raises(ModelConfigurationError):
            ModelRegistry(config_path=temp_path)
    finally:
        temp_path.unlink(missing_ok=True)
