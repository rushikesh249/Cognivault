import pytest
import tempfile
from pathlib import Path
import yaml

from backend.app.core.config import RoutingSettings, TaskRequirementConfig, load_settings
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.router import ModelRouter
from backend.app.models.schema import TaskRequirement


@pytest.fixture
def standard_registry():
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
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        temp_path = Path(f.name)

    reg = ModelRegistry(config_path=temp_path)
    yield reg
    temp_path.unlink(missing_ok=True)


def test_declarative_task_requirement_resolution():
    # Test resolving TRD Table 34 task requirements from app configuration
    doc_req = ModelRouter.get_requirement_for_task_type("document")
    assert doc_req.preferred_role == "general"
    assert doc_req.modality == "text"
    assert "reasoning" in doc_req.capabilities
    assert "document_analysis" in doc_req.capabilities

    code_req = ModelRouter.get_requirement_for_task_type("coding")
    assert code_req.preferred_role == "coding"
    assert code_req.modality == "text"
    assert "coding" in code_req.capabilities
    assert "debugging" in code_req.capabilities
    assert "testing" in code_req.capabilities

    vision_req = ModelRouter.get_requirement_for_task_type("vision")
    assert vision_req.preferred_role == "vision"
    assert vision_req.modality == "image"
    assert "image_analysis" in vision_req.capabilities


def test_unknown_task_type_raises_value_error():
    with pytest.raises(ValueError) as exc_info:
        ModelRouter.get_requirement_for_task_type("unsupported_category")
    assert "Unknown task_type 'unsupported_category'" in str(exc_info.value)
    assert "document" in str(exc_info.value)


def test_select_for_task_type_deterministic(standard_registry):
    # Flow 1 (document) -> local-general-model
    m_doc = ModelRouter.select_for_task_type("document", standard_registry, enforce_availability=False)
    assert m_doc == "local-general-model"

    # Flow 2 (coding) -> local-coding-model
    m_code = ModelRouter.select_for_task_type("coding", standard_registry, enforce_availability=False)
    assert m_code == "local-coding-model"

    # Flow 3 (vision) -> local-vision-model
    m_vision = ModelRouter.select_for_task_type("vision", standard_registry, enforce_availability=False)
    assert m_vision == "local-vision-model"


def test_custom_task_type_via_configuration_only(standard_registry):
    # TRD §14.1: adding a fourth task type is purely a configuration change, no code touched
    custom_routing = RoutingSettings(
        task_requirements={
            "audit_compliance": TaskRequirementConfig(
                preferred_role="general",
                capabilities=["reasoning"],
                modality="text",
            )
        }
    )
    req = ModelRouter.get_requirement_for_task_type("audit_compliance", routing_settings=custom_routing)
    assert req.task_type == "audit_compliance"
    assert req.preferred_role == "general"

    selected = ModelRouter.select_for_task_type(
        "audit_compliance", standard_registry, enforce_availability=False, routing_settings=custom_routing
    )
    assert selected == "local-general-model"
