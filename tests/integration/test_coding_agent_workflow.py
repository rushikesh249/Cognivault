"""Integration Test Suite for Autonomous Coding Agent Workflow (Self-Correction, Docker Sandbox & Artifacts)."""

import pytest
from pathlib import Path
import shutil
import uuid

from backend.app.agent.graph import agent_graph
from backend.app.core.config import settings
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.router import ModelRouter
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context
from backend.app.persistence.task_repository import TaskRepository
from backend.app.sandbox.docker_runner import DockerRunner, get_docker_runner
from backend.app.persistence.db import init_db


@pytest.fixture(autouse=True)
def check_docker():
    init_db()
    if not DockerRunner().is_available():
        pytest.skip("Docker engine is not running on this host environment")


def test_coding_task_classification_and_routing():
    """Verify coding task detection, local model selection, and tool gating."""
    registry = ModelRegistry()
    selected_model = ModelRouter.select_for_task_type("coding", registry=registry, enforce_availability=False)
    assert selected_model == "local-coding-model"

    # Verify Docker runner is active and healthy
    runner = get_docker_runner()
    assert runner.is_available() is True


def test_coding_workflow_self_correction_and_artifact_generation():
    """Verify autonomous cyclic self-correction in LangGraph and deliverable artifact persistence."""
    task_id = str(uuid.uuid4())
    
    # Set up task in database
    with get_db_context() as session:
        t_repo = TaskRepository(session)
        t_repo.create(
            task_id=task_id,
            title="Factorial Self-Correction Test",
            task_type="coding",
            prompt="Write a recursive factorial algorithm with unit tests and execute inside Docker sandbox.",
        )

    # Set up sandbox workspace with an initially failing test
    workspace_dir = Path(settings.paths.data_dir) / "sandbox" / task_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    test_file_content = """import pytest
from factorial import factorial

def test_factorial_base():
    assert factorial(0) == 1
    assert factorial(1) == 1

def test_factorial_positive():
    assert factorial(5) == 120

def test_factorial_negative():
    with pytest.raises(ValueError):
        factorial(-1)
"""
    (workspace_dir / "test_factorial.py").write_text(test_file_content, encoding="utf-8")

    # Initial buggy implementation
    buggy_factorial = """def factorial(n: int) -> int:
    return 0  # Buggy implementation
"""
    (workspace_dir / "factorial.py").write_text(buggy_factorial, encoding="utf-8")

    initial_state = {
        "task_id": task_id,
        "task_type": "coding",
        "goal": "Write recursive factorial with unit tests and self-correct defects.",
        "iteration": 0,
        "max_iterations": 4,
        "plan": [],
        "current_step_index": 0,
        "selected_model_id": "local-coding-model",
        "tool_calls": [],
        "observations": [],
        "validation_passed": False,
        "validation_notes": None,
        "status": "running",
        "final_artifact_id": None,
        "_staged_tool_call": None,
        "_raw_execution_result": None,
    }

    # Execute workflow graph
    final_state = agent_graph.invoke(initial_state)

    assert final_state["status"] == "succeeded"
    assert final_state["validation_passed"] is True
    assert final_state["iteration"] >= 2  # Proves self-correction loop ran!

    # Verify code artifact was persisted
    with get_db_context() as session:
        art_repo = ArtifactRepository(session)
        arts = art_repo.list_by_task_id(task_id)
        assert len(arts) > 0
        code_art = arts[0]
        assert code_art.kind == "code"
        assert Path(code_art.storage_path).exists()
        content = Path(code_art.storage_path).read_text(encoding="utf-8")
        assert "def factorial" in content
        assert "return n * factorial(n - 1)" in content

    # Clean up workspace
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)
