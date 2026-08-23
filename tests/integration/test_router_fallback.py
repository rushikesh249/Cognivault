import pytest
import tempfile
from pathlib import Path
import yaml

from backend.app.models.exceptions import ModelUnavailable
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.router import ModelRouter
from backend.app.models.schema import TaskRequirement


@pytest.fixture
def real_models_registry():
    # Load from the real configs/models.yaml populated in Phase 2
    root = Path(__file__).resolve().parent.parent.parent
    config_path = root / "configs" / "models.yaml"
    return ModelRegistry(config_path=config_path)


def test_prd_metric_4_different_model_selection(real_models_registry):
    """
    PRD Success Metric #4:
    Model Router visibly selects different model_ids for at least two task categories.
    """
    model_doc = ModelRouter.select_for_task_type("document", real_models_registry, enforce_availability=False)
    model_code = ModelRouter.select_for_task_type("coding", real_models_registry, enforce_availability=False)
    model_vision = ModelRouter.select_for_task_type("vision", real_models_registry, enforce_availability=False)

    assert model_doc == "local-general-model"
    assert model_code == "local-coding-model"
    assert model_vision == "local-vision-model"

    # Confirms visibly distinct model_ids selected
    assert model_doc != model_code
    assert model_doc != model_vision
    assert model_code != model_vision


def test_fallback_chain_when_specialized_model_disabled():
    """
    TRD §15.2 / ADR-014:
    When a specialized model is disabled (e.g. constrained VRAM / model disabled),
    the router initiates the fallback chain and falls back to an available general candidate.
    """
    data = {
        "models": [
            {
                "model_id": "local-general-model",
                "role": "general",
                "capabilities": ["reasoning", "document_analysis", "planning", "coding"],
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
                "enabled": False,  # Deliberately disabled
            },
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        temp_path = Path(f.name)

    try:
        reg = ModelRegistry(config_path=temp_path)
        # Request coding task: local-coding-model is disabled, so it should fall back to local-general-model
        req = TaskRequirement(
            task_type="coding",
            preferred_role="coding",
            modality="text",
            capabilities=["coding"],
        )
        selected = ModelRouter.select(req, reg, enforce_availability=False)
        assert selected == "local-general-model"
    finally:
        temp_path.unlink(missing_ok=True)


def test_zero_cloud_fallback_on_unsupported_requirement(real_models_registry):
    """
    Sovereignty constraint:
    If no local model satisfies the requirement, raise ModelUnavailable; NEVER fall back to cloud.
    """
    req = TaskRequirement(
        task_type="unsupported",
        preferred_role="unknown_role",
        modality="audio",  # Modality not supported by any local model
        capabilities=["speech_recognition"],
    )
    with pytest.raises(ModelUnavailable) as exc_info:
        ModelRouter.select(req, real_models_registry, enforce_availability=False)
    assert "No suitable local model available" in str(exc_info.value)
