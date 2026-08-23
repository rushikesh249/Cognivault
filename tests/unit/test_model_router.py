import tempfile
from pathlib import Path
import httpx
import pytest
import yaml

from backend.app.models.exceptions import ModelUnavailable
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.ollama_adapter import OllamaAdapter
from backend.app.models.router import ModelRouter
from backend.app.models.schema import TaskRequirement


@pytest.fixture
def sample_registry():
    data = {
        "models": [
            {
                "model_id": "local-general-model",
                "role": "general",
                "capabilities": ["reasoning", "document_analysis", "planning"],
                "modalities": ["text"],
                "context_length": 8192,
                "vram_gb": 5.5,
                "model_path": "ollama://qwen2.5:7b-instruct",
                "enabled": True,
            },
            {
                "model_id": "local-coding-model",
                "role": "coding",
                "capabilities": ["coding", "debugging", "testing"],
                "modalities": ["text"],
                "context_length": 8192,
                "vram_gb": 5.5,
                "model_path": "ollama://qwen2.5-coder:7b",
                "enabled": True,
            },
            {
                "model_id": "local-vision-model",
                "role": "vision",
                "capabilities": ["image_analysis", "document_vision"],
                "modalities": ["text", "image"],
                "context_length": 4096,
                "vram_gb": 6.0,
                "model_path": "ollama://llava:7b",
                "enabled": True,
            },
            {
                "model_id": "local-general-small",
                "role": "general",
                "capabilities": ["reasoning"],
                "modalities": ["text"],
                "context_length": 4096,
                "vram_gb": 3.0,
                "model_path": "ollama://qwen2.5:3b",
                "enabled": True,
            },
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        temp_path = Path(f.name)

    reg = ModelRegistry(config_path=temp_path)
    yield reg
    temp_path.unlink(missing_ok=True)


def test_deterministic_routing_for_document_task(sample_registry):
    req = TaskRequirement(
        task_type="document",
        preferred_role="general",
        modality="text",
        capabilities=["reasoning", "document_analysis"],
    )
    selected = ModelRouter.select(req, sample_registry, enforce_availability=False)
    assert selected == "local-general-model"


def test_deterministic_routing_for_coding_task(sample_registry):
    req = TaskRequirement(
        task_type="coding",
        preferred_role="coding",
        modality="text",
        capabilities=["coding", "debugging"],
    )
    selected = ModelRouter.select(req, sample_registry, enforce_availability=False)
    assert selected == "local-coding-model"


def test_deterministic_routing_for_vision_task(sample_registry):
    req = TaskRequirement(
        task_type="vision",
        preferred_role="vision",
        modality="image",
        capabilities=["image_analysis"],
    )
    selected = ModelRouter.select(req, sample_registry, enforce_availability=False)
    assert selected == "local-vision-model"


def test_hardware_vram_constraint_routing(sample_registry):
    # If max_vram_gb is restricted to 4.0 GB, local-general-model (5.5 GB) is filtered out
    # and local-general-small (3.0 GB) is selected
    req = TaskRequirement(
        task_type="document",
        preferred_role="general",
        modality="text",
        capabilities=["reasoning"],
        max_vram_gb=4.0,
    )
    selected = ModelRouter.select(req, sample_registry, enforce_availability=False)
    assert selected == "local-general-small"


def test_fallback_chain_triggering(sample_registry):
    # Request capabilities that only exist across general models but specify an unknown role
    req = TaskRequirement(
        preferred_role="specialist_unknown",
        modality="text",
        capabilities=["reasoning", "document_analysis"],
    )
    selected = ModelRouter.select(req, sample_registry, enforce_availability=False)
    assert selected == "local-general-model"


def test_no_suitable_model_raises_model_unavailable(sample_registry):
    # Request capability not supported by any registered model
    req = TaskRequirement(
        modality="text",
        capabilities=["quantum_simulation", "satellite_telemetry"],
    )
    with pytest.raises(ModelUnavailable) as exc_info:
        ModelRouter.select(req, sample_registry, enforce_availability=False)
    assert "No suitable local model available" in str(exc_info.value)
