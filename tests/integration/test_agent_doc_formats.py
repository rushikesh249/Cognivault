"""Integration tests for Multi-Format Document Generation via Agent Graph (TRD Section 11, 20, 22)."""

import uuid
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from backend.app.agent.graph import agent_graph
from backend.app.agent.state import AgentState
from backend.app.main import app
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.task_repository import TaskRepository
from backend.app.tools.base import ToolContext, ToolPermissionError
from backend.app.tools.tool_registry import get_tool_registry


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def test_agent_generates_xlsx_flow(client):
    """Test full agent flow generating XLSX spreadsheet artifact from start to API retrieval."""
    goal = f"Analyze refinery inspection report and generate technical summary spreadsheet XLSX ({uuid.uuid4().hex[:6]})."

    with get_db_context() as session:
        t_repo = TaskRepository(session)
        task = t_repo.create(title="Refinery Inspection Spreadsheet", task_type="document", prompt=goal)
        task_id = task.task_id

    initial_state: AgentState = {
        "task_id": task_id,
        "task_type": "document",
        "goal": goal,
        "iteration": 0,
        "max_iterations": 4,
        "current_step_index": 0,
        "plan": [],
        "observations": [],
        "tool_calls": [],
        "validation_passed": False,
        "validation_notes": "",
        "selected_model_id": "local-default",
        "final_artifact_id": None,
        "status": "running",
        "error": None,
        "_staged_tool_call": None,
        "_raw_execution_result": None,
    }

    final_state = agent_graph.invoke(initial_state, config={"recursion_limit": 100})

    assert final_state["status"] == "succeeded"
    assert final_state["validation_passed"] is True
    artifact_id = final_state.get("final_artifact_id")
    assert artifact_id is not None

    with get_db_context() as session:
        a_repo = ArtifactRepository(session)
        art = a_repo.get_by_id(artifact_id)
        assert art is not None
        assert art.kind == "xlsx"
        assert Path(art.storage_path).exists()

    # API Retrieval: Binary Download
    res_bin = client.get(f"/api/artifacts/{artifact_id}")
    assert res_bin.status_code == 200
    assert "spreadsheetml" in res_bin.headers["content-type"]

    # API Retrieval: Metadata
    res_meta = client.get(f"/api/artifacts/{artifact_id}?meta=true")
    assert res_meta.status_code == 200
    assert res_meta.json()["kind"] == "xlsx"


def test_agent_generates_pptx_flow(client):
    """Test full agent flow generating PPTX presentation deck."""
    goal = f"Prepare executive management summary presentation deck in PPTX format ({uuid.uuid4().hex[:6]})."

    with get_db_context() as session:
        t_repo = TaskRepository(session)
        task = t_repo.create(title="Executive Presentation Deck", task_type="document", prompt=goal)
        task_id = task.task_id

    initial_state: AgentState = {
        "task_id": task_id,
        "task_type": "document",
        "goal": goal,
        "iteration": 0,
        "max_iterations": 4,
        "current_step_index": 0,
        "plan": [],
        "observations": [],
        "tool_calls": [],
        "validation_passed": False,
        "validation_notes": "",
        "selected_model_id": "local-default",
        "final_artifact_id": None,
        "status": "running",
        "error": None,
        "_staged_tool_call": None,
        "_raw_execution_result": None,
    }

    final_state = agent_graph.invoke(initial_state, config={"recursion_limit": 100})

    assert final_state["status"] == "succeeded"
    assert final_state["validation_passed"] is True
    artifact_id = final_state.get("final_artifact_id")
    assert artifact_id is not None

    with get_db_context() as session:
        a_repo = ArtifactRepository(session)
        art = a_repo.get_by_id(artifact_id)
        assert art is not None
        assert art.kind == "pptx"
        assert Path(art.storage_path).exists()

    res_bin = client.get(f"/api/artifacts/{artifact_id}")
    assert res_bin.status_code == 200
    assert "presentationml" in res_bin.headers["content-type"]


def test_agent_generates_pdf_flow(client):
    """Test full agent flow generating PDF inspection report."""
    goal = f"Generate a formal technical compliance report in PDF format ({uuid.uuid4().hex[:6]})."

    with get_db_context() as session:
        t_repo = TaskRepository(session)
        task = t_repo.create(title="Formal Inspection Report PDF", task_type="document", prompt=goal)
        task_id = task.task_id

    initial_state: AgentState = {
        "task_id": task_id,
        "task_type": "document",
        "goal": goal,
        "iteration": 0,
        "max_iterations": 4,
        "current_step_index": 0,
        "plan": [],
        "observations": [],
        "tool_calls": [],
        "validation_passed": False,
        "validation_notes": "",
        "selected_model_id": "local-default",
        "final_artifact_id": None,
        "status": "running",
        "error": None,
        "_staged_tool_call": None,
        "_raw_execution_result": None,
    }

    final_state = agent_graph.invoke(initial_state, config={"recursion_limit": 100})

    assert final_state["status"] == "succeeded"
    assert final_state["validation_passed"] is True
    artifact_id = final_state.get("final_artifact_id")
    assert artifact_id is not None

    with get_db_context() as session:
        a_repo = ArtifactRepository(session)
        art = a_repo.get_by_id(artifact_id)
        assert art is not None
        assert art.kind == "pdf"
        assert Path(art.storage_path).exists()

    res_bin = client.get(f"/api/artifacts/{artifact_id}")
    assert res_bin.status_code == 200
    assert "application/pdf" in res_bin.headers["content-type"]


def test_coding_and_vision_tasks_cannot_invoke_document_tools():
    """Verify security isolation: coding and vision task contexts cannot execute document generation tools."""
    reg = get_tool_registry()

    doc_tools = ["create_docx", "create_xlsx", "create_pptx", "create_pdf"]
    for task_type in ["coding", "vision"]:
        ctx = ToolContext(task_id=f"sec-check-{task_type}", task_type=task_type)
        for t_name in doc_tools:
            with pytest.raises(ToolPermissionError):
                reg.invoke(t_name, {"template": "test", "data": {}}, ctx)
