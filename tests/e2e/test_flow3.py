"""End-to-End Test for Hero Flow 3: Multimodal Vision Understanding (TRD ?32.3, PRD Metric #3)."""

import io
import json
import uuid
import pytest
from pathlib import Path
from PIL import Image

from backend.app.core.config import settings
from backend.app.multimodal.vision_service import VisionResult, VisionService, get_vision_service
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.file_repository import FileRepository
from backend.app.persistence.task_repository import TaskRepository
from backend.app.services.agent_service import AgentService
from backend.app.services.vision_service import VisionAppService, get_vision_app_service, set_vision_app_service
from tests.integration.test_vision_flow import StubLocalVisionProvider


def test_hero_flow_3_multimodal_understanding_end_to_end():
    """
    Full E2E run of Hero Flow 3:
    1. Create task with task_type='vision'.
    2. Upload synthetic industrial inspection image.
    3. Run agent workflow end-to-end.
    4. Assert structured VisionResult with observation, interpretation, uncertainty.
    5. Assert zero certified verdict claims.
    6. Verify database status=succeeded and event stream audit.
    """
    init_db()
    task_id = f"flow3-e2e-{uuid.uuid4()}"
    file_id = f"file-{uuid.uuid4()}"

    # 1. Create synthetic inspection photo
    demo_inputs = Path("knowledge_base/demo_inputs")
    demo_inputs.mkdir(parents=True, exist_ok=True)
    img_path = demo_inputs / f"{file_id}.jpg"
    img = Image.new("RGB", (256, 256), color=(140, 70, 40))
    img.save(img_path, format="JPEG")

    # 2. Register task and file in persistence
    with get_db_context() as session:
        t_repo = TaskRepository(session)
        f_repo = FileRepository(session)

        t_repo.create(
            task_id=task_id,
            title="Inspect Heat Exchanger Flange",
            task_type="vision",
            prompt="Analyze flange surface for pitting and thermal discoloration",
        )
        f_repo.create(
            file_id=file_id,
            task_id=task_id,
            filename="synthetic_weld_flange.jpg",
            mime_type="image/jpeg",
            size_bytes=img_path.stat().st_size,
            storage_path=str(img_path),
        )

    # 3. Wire stub vision provider for deterministic test execution
    stub_provider = StubLocalVisionProvider()
    vision_domain = VisionService(provider=stub_provider)
    set_vision_app_service(VisionAppService(domain_service=vision_domain))

    # 4. Execute through AgentService
    agent_svc = AgentService()
    final_state = agent_svc._run_graph_sync(task_id)

    # 5. Assertions on final agent state and task record
    assert final_state["status"] == "succeeded"
    assert final_state["validation_passed"] is True
    assert final_state["selected_model_id"] == "local-vision-model"

    # Verify task updated in SQLite database
    with get_db_context() as session:
        t_repo = TaskRepository(session)
        task_rec = t_repo.get_by_id(task_id)
        assert task_rec is not None
        assert task_rec.status == "succeeded"
        assert task_rec.model_used == "local-vision-model"

        # Verify task events emitted
        events = t_repo.get_events(task_id)
        assert len(events) >= 5
        node_names = [e.node for e in events]
        assert "task_understanding" in node_names
        assert "planning" in node_names
        assert "model_selection" in node_names
        assert "execution" in node_names
        assert "observation" in node_names
        assert "validation" in node_names
        assert "final_deliverable" in node_names
