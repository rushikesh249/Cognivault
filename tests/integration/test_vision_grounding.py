"""Regression test suite for Vision Grounding, Model Routing, and Deliverable Generation."""

import io
import json
import uuid
import docx
import pytest
from pathlib import Path
from PIL import Image

from backend.app.agent.graph import agent_graph
from backend.app.agent.state import AgentState
from backend.app.core.config import settings
from backend.app.models.exceptions import ModelUnavailable
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.provider import ModelProvider
from backend.app.models.router import ModelRouter
from backend.app.models.schema import ModelConfig, ModelStatus, ProviderStatus
from backend.app.multimodal.vision_service import VisionResult, VisionService
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.file_repository import FileRepository
from backend.app.persistence.task_repository import TaskRepository
from backend.app.services.agent_service import AgentService
from backend.app.services.vision_service import (
    VisionAppService,
    get_vision_app_service,
    set_vision_app_service,
)


class MockLLaVAProvider(ModelProvider):
    """Mock provider capturing multimodal request parameters for inspection."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.last_model_id = None
        self.last_prompt = None
        self.last_images = None

    def is_provider_available(self) -> bool:
        return not self.should_fail

    def is_model_available(self, model_identifier: str) -> bool:
        return not self.should_fail

    def get_provider_status(self) -> ProviderStatus:
        return ProviderStatus.UNAVAILABLE if self.should_fail else ProviderStatus.AVAILABLE

    def get_model_status(self, model_config: ModelConfig) -> ModelStatus:
        return ModelStatus.UNAVAILABLE if self.should_fail else ModelStatus.AVAILABLE

    def list_available_models(self):
        return [] if self.should_fail else ["llava:7b-v1.5-q4_K_M"]

    def ensure_loaded(self, model_id: str) -> bool:
        if self.should_fail:
            raise ModelUnavailable("VLM not available")
        return True

    def unload(self, model_id: str) -> bool:
        return True

    def unload_lru(self) -> bool:
        return True

    def generate(self, model_id: str, prompt: str, images=None, system=None, format=None, stream=False) -> str:
        if self.should_fail:
            raise ModelUnavailable("Local vision model unavailable: connection error")
        self.last_model_id = model_id
        self.last_prompt = prompt
        self.last_images = images

        return json.dumps({
            "observation": [
                "Severe surface oxidation and rust accumulation on bolted pipe flange",
                "Four 1-inch carbon steel bolts exhibiting visible corrosive pitting",
                "White industrial vessel background with localized discoloration",
            ],
            "interpretation": [
                "Atmospheric corrosion caused by external moisture accumulation",
                "Crevice corrosion likely active under bolt head washers",
            ],
            "uncertainty": [
                "Internal wall thinning or stress cracking cannot be determined visually",
                "Non-certified visual assessment only - requires ultrasonic thickness gauge",
            ],
        })


def test_vision_task_selects_local_vision_model_and_passes_image():
    """Verify Vision task selects local-vision-model and delivers Base64 image to LLaVA."""
    init_db()
    task_id = f"vis-test-{uuid.uuid4()}"
    file_id = f"file-{uuid.uuid4()}"

    # 1. Create test image on disk
    demo_inputs = Path("knowledge_base/demo_inputs")
    demo_inputs.mkdir(parents=True, exist_ok=True)
    img_path = demo_inputs / f"{file_id}.jpg"
    img = Image.new("RGB", (128, 128), color=(200, 100, 50))
    img.save(img_path, format="JPEG")

    # 2. Register task and file in persistence
    goal = "Analyze the uploaded equipment inspection image. Identify visual anomalies and generate report as DOCX."
    with get_db_context() as session:
        TaskRepository(session).create(
            task_id=task_id,
            title="Equipment Corrosion Inspection",
            task_type="vision",
            prompt=goal,
        )
        FileRepository(session).create(
            file_id=file_id,
            task_id=task_id,
            filename="test 1.jpg",
            mime_type="image/jpeg",
            size_bytes=img_path.stat().st_size,
            storage_path=str(img_path),
        )

    # 3. Setup mock provider
    mock_provider = MockLLaVAProvider(should_fail=False)
    vision_domain = VisionService(provider=mock_provider)
    vision_app = VisionAppService(domain_service=vision_domain)
    set_vision_app_service(vision_app)

    # 4. Run agent
    agent_svc = AgentService()
    final_state = agent_svc._run_graph_sync(task_id)

    # 5. Assertions
    assert final_state["status"] == "succeeded"
    assert final_state["selected_model_id"] == "local-vision-model"

    # Verify LLaVA provider received the right model and images
    assert "llava:7b-v1.5-q4_K_M" in mock_provider.last_model_id
    assert mock_provider.last_images is not None
    assert len(mock_provider.last_images) == 1
    assert len(mock_provider.last_images[0]) > 50  # Base64 string

    # Verify DOCX artifact generated
    artifact_id = final_state.get("final_artifact_id")
    assert artifact_id is not None

    with get_db_context() as session:
        art = ArtifactRepository(session).get_by_id(artifact_id)
        assert art is not None
        assert art.kind == "docx"

        doc = docx.Document(art.storage_path)
        doc_text = " ".join(p.text for p in doc.paragraphs)

        # Must contain visual findings
        assert "Visual Observations" in doc_text
        assert "Severe surface oxidation and rust accumulation" in doc_text
        assert "Four 1-inch carbon steel bolts" in doc_text

        # Must claim local-vision-model, NEVER local-general-model
        assert "local-vision-model" in doc_text
        assert "local-general-model" not in doc_text

        # Must not contain generic document analysis fallback
        assert "No critical findings identified" not in doc_text


def test_vision_task_never_silently_falls_back_to_general_model_on_failure():
    """Verify that when the vision model is unavailable, the task fails rather than faking output."""
    init_db()
    task_id = f"vis-fail-{uuid.uuid4()}"
    file_id = f"file-{uuid.uuid4()}"

    demo_inputs = Path("knowledge_base/demo_inputs")
    demo_inputs.mkdir(parents=True, exist_ok=True)
    img_path = demo_inputs / f"{file_id}.jpg"
    img = Image.new("RGB", (64, 64), color=(50, 50, 50))
    img.save(img_path, format="JPEG")

    goal = "Analyze the uploaded equipment inspection image and generate report."
    with get_db_context() as session:
        TaskRepository(session).create(
            task_id=task_id,
            title="Equipment Inspection Fail Test",
            task_type="vision",
            prompt=goal,
        )
        FileRepository(session).create(
            file_id=file_id,
            task_id=task_id,
            filename="test_fail.jpg",
            mime_type="image/jpeg",
            size_bytes=img_path.stat().st_size,
            storage_path=str(img_path),
        )

    # Wire a failing provider
    failing_provider = MockLLaVAProvider(should_fail=True)
    vision_domain = VisionService(provider=failing_provider)
    set_vision_app_service(VisionAppService(domain_service=vision_domain))

    agent_svc = AgentService()
    final_state = agent_svc._run_graph_sync(task_id)

    # Must fail explicitly with error status, never succeed with generic fallback
    assert final_state["status"] in ["failed", "failed_bounded"]
    assert final_state["validation_passed"] is False

    with get_db_context() as session:
        task_rec = TaskRepository(session).get_by_id(task_id)
        assert task_rec.status in ["failed", "failed_bounded"]
        # No artifact created
        arts = ArtifactRepository(session).list_by_task_id(task_id)
        assert len(arts) == 0
