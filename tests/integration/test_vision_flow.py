"""Integration tests for Hero Flow 3 Multimodal Understanding (TRD ?21, ?32.3, ADR-007)."""

import io
import json
import uuid
import pytest
from pathlib import Path
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.agent.graph import agent_graph
from backend.app.agent.state import AgentState
from backend.app.api.files import router as files_router
from backend.app.api.vision import router as vision_router
from backend.app.core.config import settings
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.provider import ModelProvider
from backend.app.models.router import ModelRouter
from backend.app.models.schema import ModelConfig, ModelStatus, ProviderStatus
from backend.app.multimodal.vision_service import VisionResult, VisionService, get_vision_service
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.file_repository import FileRepository
from backend.app.persistence.task_repository import TaskRepository
from backend.app.services.vision_service import VisionAppService, get_vision_app_service, set_vision_app_service
from backend.app.tools.base import ToolContext, ToolPermissionError
from backend.app.tools.tool_registry import ToolRegistry


class StubLocalVisionProvider(ModelProvider):
    """Deterministic local VLM stub for integration testing."""

    def is_provider_available(self) -> bool:
        return True

    def is_model_available(self, model_identifier: str) -> bool:
        return True

    def get_provider_status(self) -> ProviderStatus:
        return ProviderStatus.AVAILABLE

    def get_model_status(self, model_config: ModelConfig) -> ModelStatus:
        return ModelStatus.AVAILABLE

    def list_available_models(self):
        return ["llava:7b-v1.5-q4_K_M"]

    def check_model_health(self, model_identifier: str = "local-vision-model") -> dict:
        return {"available": True, "provider_online": True, "model_found": True, "message": "Model available"}

    def ensure_loaded(self, model_id: str) -> bool:
        return True

    def unload(self, model_id: str) -> bool:
        return True

    def unload_lru(self) -> bool:
        return True

    def generate(self, model_id: str, prompt: str, images=None, system=None, format=None, stream=False) -> str:
        return json.dumps({
            "observation": [
                "Discoloration on secondary flange valve ring",
                "Minor surface oxidation at 6 o'clock bolt",
            ],
            "interpretation": [
                "Early-stage atmospheric corrosion from intermittent moisture",
            ],
            "uncertainty": [
                "Specular reflection on top quadrant limits visual confirmation",
            ],
        })


@pytest.fixture
def integration_client():
    init_db()
    app = FastAPI()
    app.include_router(files_router)
    app.include_router(vision_router)
    return TestClient(app)


def test_flow3_upload_to_vision_result_roundtrip(integration_client: TestClient):
    """Verify integration flow: File Upload -> Vision Analysis -> VisionResult."""
    # 1. Setup mock vision service
    mock_provider = StubLocalVisionProvider()
    vision_domain = VisionService(provider=mock_provider)
    vision_app = VisionAppService(domain_service=vision_domain)
    set_vision_app_service(vision_app)

    # 2. Upload test image via POST /api/files/upload
    img = Image.new("RGB", (128, 128), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    upload_resp = integration_client.post(
        "/api/files/upload",
        files={"file": ("pipe_flange.jpg", buf, "image/jpeg")},
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["file_id"]

    # 3. Call POST /api/vision/analyze
    from backend.app.api.vision import get_vision_app_service as api_get_vision_app
    integration_client.app.dependency_overrides[api_get_vision_app] = lambda: vision_app

    analyze_resp = integration_client.post(
        "/api/vision/analyze",
        json={"file_id": file_id, "prompt": "Identify potential corrosion sites"},
    )
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert "observation" in data
    assert len(data["observation"]) == 2
    assert "Discoloration" in data["observation"][0]
    assert data["model_used"] == "local-vision-model"


def test_model_router_to_vision_model_resolution():
    """Verify ModelRouter selects local-vision-model for task_type='vision'."""
    registry = ModelRegistry()
    selected_id = ModelRouter.select_for_task_type(
        task_type="vision",
        registry=registry,
        enforce_availability=False,
    )
    assert selected_id == "local-vision-model"
    model_cfg = registry.get(selected_id)
    assert model_cfg.role == "vision"
    assert "image_analysis" in model_cfg.capabilities
    assert "image" in model_cfg.modalities


def test_agent_graph_executes_vision_task():
    """Verify LangGraph 8-node loop execution for task_type='vision'."""
    init_db()
    task_id = f"vis-agent-task-{uuid.uuid4()}"

    # 1. Register synthetic image in DB and uploads dir
    img_dir = settings.paths.uploads_dir
    img_dir.mkdir(parents=True, exist_ok=True)
    img_file = img_dir / f"{task_id}.jpg"
    img = Image.new("RGB", (64, 64), color=(80, 80, 80))
    img.save(img_file, format="JPEG")

    with get_db_context() as session:
        file_repo = FileRepository(session)
        task_repo = TaskRepository(session)

        task_repo.create(
            task_id=task_id,
            title="Inspect Flange",
            task_type="vision",
            prompt="Analyze valve joint for corrosion",
        )
        file_repo.create(
            file_id=task_id,
            task_id=task_id,
            filename="flange.jpg",
            mime_type="image/jpeg",
            size_bytes=img_file.stat().st_size,
            storage_path=str(img_file),
        )

    # 2. Inject stub vision provider
    stub_provider = StubLocalVisionProvider()
    vision_domain = VisionService(provider=stub_provider)
    set_vision_app_service(VisionAppService(domain_service=vision_domain))

    # 3. Invoke LangGraph agent
    initial_state: AgentState = {
        "task_id": task_id,
        "task_type": "vision",
        "goal": "Analyze valve joint for corrosion",
        "plan": [],
        "current_step_index": 0,
        "iteration": 0,
        "max_iterations": 3,
        "selected_model_id": None,
        "tool_calls": [],
        "observations": [],
        "validation_passed": False,
        "validation_notes": None,
        "final_artifact_id": None,
        "status": "running",
        "error": None,
    }

    final_state = agent_graph.invoke(initial_state, config={"recursion_limit": 50})
    assert final_state["status"] == "succeeded"
    assert final_state["validation_passed"] is True
    assert final_state["selected_model_id"] == "local-vision-model"
    assert len(final_state["observations"]) > 0


def test_vision_task_zero_tool_permission_enforcement():
    """Verify ToolRegistry strictly enforces 0 tools for vision tasks (TRD Table 31)."""
    registry = ToolRegistry()
    ctx = ToolContext(task_id="vis-tool-test", task_type="vision")

    assert len(registry.list_tools(task_type="vision")) == 0

    # Ensure OCR tool cannot be called in vision task
    with pytest.raises(ToolPermissionError):
        registry.invoke("extract_text_from_scan", {"file_id": "any", "page": 1}, ctx)

    # Ensure code tools cannot be called in vision task
    with pytest.raises(ToolPermissionError):
        registry.invoke("execute_code", {"language": "python", "code": "print(1)"}, ctx)
