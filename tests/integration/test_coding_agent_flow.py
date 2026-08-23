"""Hero Flow 2 End-to-End Integration Test (TRD Section 20, Table 44, Test Plan Section 10)."""

import shutil
from pathlib import Path
from unittest.mock import patch
import pytest

from backend.app.agent.graph import agent_graph
from backend.app.agent.nodes.tool_selection import tool_selection_node
from backend.app.agent.state import AgentState
from backend.app.core.config import settings
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.task_repository import TaskRepository
from backend.app.sandbox.docker_runner import DockerRunner, ServiceUnavailableError
from backend.app.tools.base import ToolContext, ToolError
from backend.app.tools.code_tools import ExecuteCodeInput, ExecuteCodeTool, RunTestsInput, RunTestsTool


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_hero_flow_2_injected_failure_self_correction_recovery():
    """
    Hero Flow 2 (TRD Section 20, Table 44, PRD Success Metric #2):
    Seeded code fails pytest in Docker -> Observation parses TestFailure ->
    Planning formulates fix -> Execution applies patch in Docker ->
    Second pytest passes -> Validation succeeds -> Status = succeeded.
    """
    goal_prompt = "Fix detected moving average calculation defect in telemetry data processor module and verify with test suite."

    # 1. Create task in SQLite
    with get_db_context() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(
            title="Hero Flow 2: Telemetry Processor Self-Correction",
            task_type="coding",
            prompt=goal_prompt,
        )
        task_id = task.task_id

    # 2. Seed task workspace in data/sandbox/{task_id} with genuine failing code from demo_seed
    workspace_dir = settings.paths.data_dir / "sandbox" / task_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    seed_src = Path("sandbox/demo_seed/data_processor.py")
    seed_test = Path("sandbox/demo_seed/test_data_processor.py")
    assert seed_src.exists() and seed_test.exists(), "Demo seed files must exist"

    shutil.copy2(seed_src, workspace_dir / "data_processor.py")
    shutil.copy2(seed_test, workspace_dir / "test_data_processor.py")

    # 3. Initialize Agent State and invoke LangGraph workflow
    initial_state: AgentState = {
        "task_id": task_id,
        "task_type": "coding",
        "goal": goal_prompt,
        "plan": [],
        "current_step_index": 0,
        "iteration": 0,
        "max_iterations": 6,
        "selected_model_id": None,
        "tool_calls": [],
        "observations": [],
        "validation_passed": False,
        "validation_notes": None,
        "final_artifact_id": None,
        "status": "running",
        "error": None,
        "_staged_tool_call": None,
        "_raw_execution_result": None,
    }

    final_state = agent_graph.invoke(initial_state, config={"recursion_limit": 100})

    # 4. State & Self-Correction Assertions
    assert final_state["status"] == "succeeded", f"Expected succeeded, got {final_state.get('status')}"
    assert final_state["validation_passed"] is True
    # Genuine self-correction cycle: iteration 1 failed tests, iteration 2 fixed & passed
    assert final_state["iteration"] == 2, f"Expected 2 iterations for self-correction, got {final_state['iteration']}"

    # 5. Verify Observation records contain both failure diagnosis and subsequent pass
    observations = final_state.get("observations", [])
    has_test_failure_obs = any(
        obs.get("structured_data", {}).get("test_failure") is not None
        for obs in observations
    )
    has_test_pass_obs = any(
        obs.get("structured_data", {}).get("passed") is True
        for obs in observations
    )
    assert has_test_failure_obs, "Observations must record the initial injected test failure"
    assert has_test_pass_obs, "Observations must record the successful test pass after correction"

    # 6. Database Task Record Verification
    with get_db_context() as session:
        task_repo = TaskRepository(session)
        updated_task = task_repo.get_by_id(task_id)
        assert updated_task is not None
        assert updated_task.status == "succeeded"
        assert updated_task.model_used == "local-coding-model"


def test_coding_agent_bounded_failure_at_max_iterations():
    """
    Verify that an unresolvable test failure cleanly terminates with
    status="failed_bounded" at iteration 6 without infinite loops.
    """
    goal_prompt = "Execute permanently failing test suite to verify bounded iteration behavior."

    with get_db_context() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(
            title="Bounded Failure Test",
            task_type="coding",
            prompt=goal_prompt,
        )
        task_id = task.task_id

    # Create workspace with a permanent failing test
    workspace_dir = settings.paths.data_dir / "sandbox" / task_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    unresolvable_test = (
        "def test_permanent_failure():\n"
        "    assert False, 'Permanent unresolvable defect'\n"
    )
    (workspace_dir / "test_unresolvable.py").write_text(unresolvable_test, encoding="utf-8")

    initial_state: AgentState = {
        "task_id": task_id,
        "task_type": "coding",
        "goal": goal_prompt,
        "plan": ["Execute test suite to detect failures"],
        "current_step_index": 0,
        "iteration": 5,  # Start at iteration 5 so next planning entry hits max_iterations=6
        "max_iterations": 6,
        "selected_model_id": None,
        "tool_calls": [],
        "observations": [],
        "validation_passed": False,
        "validation_notes": "Permanent failure",
        "final_artifact_id": None,
        "status": "running",
        "error": None,
        "_staged_tool_call": None,
        "_raw_execution_result": None,
    }

    final_state = agent_graph.invoke(initial_state, config={"recursion_limit": 100})
    assert final_state["status"] == "failed_bounded"
    assert final_state["iteration"] == 6
    assert final_state["validation_passed"] is False


def test_coding_agent_unauthorized_tool_rejection():
    """Verify that coding tasks reject document/knowledge tools before ToolRegistry dispatch."""
    state: AgentState = {
        "task_id": "test-sec-task",
        "task_type": "coding",
        "goal": "Test security boundary",
        "plan": ["Search knowledge base for secrets", "Generate docx approval note"],
        "current_step_index": 0,
        "iteration": 1,
        "max_iterations": 6,
        "selected_model_id": "local-coding-model",
        "tool_calls": [],
        "observations": [],
        "validation_passed": False,
        "validation_notes": None,
        "final_artifact_id": None,
        "status": "running",
        "error": None,
        "_staged_tool_call": None,
        "_raw_execution_result": None,
    }

    result = tool_selection_node(state)
    assert result["_staged_tool_call"] is None, "Unauthorized tools must be rejected for coding task_type"


def test_coding_agent_docker_isolation_and_no_host_fallback():
    """Verify Docker unavailability raises 503 ToolError and NEVER executes on host."""
    runner = DockerRunner()
    exec_tool = ExecuteCodeTool(runner=runner)
    test_tool = RunTestsTool(runner=runner)
    ctx = ToolContext(task_id="sec-test", task_type="coding")

    with patch.object(runner, "run", side_effect=ServiceUnavailableError("Docker daemon offline")):
        with pytest.raises(ToolError, match="503 ServiceUnavailable"):
            exec_tool.execute(ExecuteCodeInput(code="print('host escape test')"), ctx)

        with pytest.raises(ToolError, match="503 ServiceUnavailable"):
            test_tool.execute(RunTestsInput(test_command="pytest"), ctx)
