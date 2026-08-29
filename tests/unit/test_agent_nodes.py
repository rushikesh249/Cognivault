"""Unit tests for all 8 LangGraph Agent Nodes in isolation (TRD Section 11.3, Table 30)."""

import pytest
from backend.app.agent.graph import should_continue_or_finalize
from backend.app.agent.nodes import (
    task_understanding_node,
    planning_node,
    model_selection_node,
    tool_selection_node,
    execution_node,
    observation_node,
    validation_node,
    final_deliverable_node,
)
from backend.app.agent.state import AgentState
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.task_repository import TaskRepository


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()


def make_initial_state(task_type="document", goal="Test goal", iteration=0, max_iter=4) -> AgentState:
    with get_db_context() as session:
        repo = TaskRepository(session)
        task = repo.create(title="Unit Test Task", task_type=task_type, prompt=goal)
        task_id = task.task_id

    return {
        "task_id": task_id,
        "task_type": task_type,
        "goal": goal,
        "plan": [],
        "current_step_index": 0,
        "iteration": iteration,
        "max_iterations": max_iter,
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


def test_task_understanding_node():
    """Verify Task Understanding normalizes goal and validates task_type."""
    state = make_initial_state(task_type="document", goal="  Review safety guidelines  ")
    out = task_understanding_node(state)
    assert out["goal"] == "Review safety guidelines"
    assert out["task_type"] == "document"


def test_planning_node_increments_iteration_counter_exclusively():
    """Verify Planning node increments iteration counter and formulates plan."""
    state = make_initial_state(iteration=0, max_iter=4)
    out = planning_node(state)
    assert out["iteration"] == 1
    assert len(out["plan"]) > 0
    assert out["current_step_index"] == 0

    # Second pass increments to 2
    state.update(out)
    out2 = planning_node(state)
    assert out2["iteration"] == 2


def test_model_selection_node():
    """Verify Model Selection node invokes ModelRouter and sets selected_model_id."""
    state = make_initial_state(task_type="coding")
    out = model_selection_node(state)
    assert out["selected_model_id"] is not None


def test_tool_selection_node_filters_tools_for_task_type():
    """Verify Tool Selection node filters tools according to permitted task_type."""
    state = make_initial_state(task_type="document")
    state["plan"] = ["Search knowledge base for SOP"]
    state["current_step_index"] = 0
    out = tool_selection_node(state)
    staged = out.get("_staged_tool_call")
    assert staged is not None
    assert staged["tool_name"] == "search_knowledge_base"


def test_execution_node_dispatches_tool_and_records_audit():
    """Verify Execution node dispatches through ToolRegistry."""
    state = make_initial_state(task_type="document")
    state["_staged_tool_call"] = {
        "tool_name": "list_files",
        "arguments": {"path": "."},
    }
    out = execution_node(state)
    assert len(out["tool_calls"]) == 1
    assert out["tool_calls"][0]["tool_name"] == "list_files"
    assert out["tool_calls"][0]["success"] is True


def test_observation_node():
    """Verify Observation node normalizes execution results and advances step index."""
    state = make_initial_state()
    state["current_step_index"] = 0
    state["_raw_execution_result"] = {
        "type": "tool",
        "tool_name": "list_files",
        "success": True,
        "data": {"entries": ["file1.txt"]},
    }
    out = observation_node(state)
    assert len(out["observations"]) == 1
    assert out["observations"][0]["node"] == "observation"
    assert out["current_step_index"] == 1


def test_validation_node_pass_and_replan_and_failed_bounded():
    """Verify Validation node routing conditions."""
    # 1. Validation passed -> succeeded
    state_pass = make_initial_state(iteration=1, max_iter=4)
    state_pass["observations"] = [{"node": "observation", "content": "Success", "level": "info"}]
    out_pass = validation_node(state_pass)
    assert out_pass["validation_passed"] is True
    assert out_pass["status"] == "succeeded"

    # 2. Validation failed & iteration < max -> running (re-plan)
    state_fail = make_initial_state(iteration=1, max_iter=4)
    state_fail["observations"] = [{"node": "observation", "content": "Tool error", "level": "error"}]
    out_fail = validation_node(state_fail)
    assert out_fail["validation_passed"] is False
    assert out_fail["status"] == "running"

    # 3. Validation failed & iteration == max -> failed_bounded
    state_bounded = make_initial_state(iteration=4, max_iter=4)
    state_bounded["observations"] = [{"node": "observation", "content": "Tool error", "level": "error"}]
    out_bounded = validation_node(state_bounded)
    assert out_bounded["validation_passed"] is False
    assert out_bounded["status"] == "failed_bounded"


def test_final_deliverable_node_persists_status():
    """Verify Final Deliverable node updates SQLite task status."""
    state = make_initial_state(task_type="coding")
    state["status"] = "succeeded"
    state["selected_model_id"] = "qwen2.5-coder:7b"
    
    out = final_deliverable_node(state)
    assert out["status"] == "succeeded"

    with get_db_context() as session:
        repo = TaskRepository(session)
        task = repo.get_by_id(state["task_id"])
        assert task.status == "succeeded"
        assert task.model_used == "qwen2.5-coder:7b"


def test_observation_node_run_tests_docker_error_never_becomes_success():
    """Regression: a run_tests ToolError (e.g. Docker 503) must never be
    converted into exit_code=0 / 'All tests passed'."""
    state = make_initial_state(task_type="coding")
    state["_raw_execution_result"] = {
        "type": "tool",
        "tool_name": "run_tests",
        "success": False,
        "error": "503 ServiceUnavailable: Docker daemon is not running or unreachable.",
    }
    out = observation_node(state)
    obs = out["observations"][0]
    sd = obs["structured_data"]

    assert obs["level"] == "error"
    assert "All tests passed" not in obs["content"]
    assert sd.get("execution_status") == "error"
    assert sd.get("error_type") == "docker_unavailable"
    assert sd.get("passed") is False
    # No synthesized pytest exit code may exist
    assert "exit_code" not in sd
    assert sd.get("data") in (None, {})


def test_observation_node_run_tests_missing_exit_code_treated_as_invalid():
    """Regression: a success=True run_tests result without exit_code must not
    be reported as a passing test suite."""
    state = make_initial_state(task_type="coding")
    state["_raw_execution_result"] = {
        "type": "tool",
        "tool_name": "run_tests",
        "success": True,
        "data": {"stdout": "", "stderr": ""},
    }
    out = observation_node(state)
    obs = out["observations"][0]
    assert obs["level"] == "error"
    assert "All tests passed" not in obs["content"]
    assert obs["structured_data"].get("execution_status") == "error"


def test_validation_infrastructure_failure_terminates_without_replan():
    """Regression: an infrastructure/tool execution error must fail validation
    with status='failed' and route directly to final_deliverable."""
    state = make_initial_state(task_type="coding", iteration=1, max_iter=6)
    state["plan"] = ["Execute test suite to detect failures"]
    state["current_step_index"] = 1
    state["observations"] = [{
        "node": "observation",
        "content": "Test runner infrastructure failure (docker_unavailable): ...",
        "level": "error",
        "structured_data": {
            "type": "tool",
            "tool_name": "run_tests",
            "success": False,
            "execution_status": "error",
            "error_type": "docker_unavailable",
            "error_message": "503 ServiceUnavailable: Docker daemon is not running or unreachable.",
            "passed": False,
        },
    }]
    out = validation_node(state)
    assert out["validation_passed"] is False
    assert out["status"] == "failed"
    assert "docker_unavailable" in out["validation_notes"]

    # Router must skip the re-plan loop entirely
    state.update(out)
    assert should_continue_or_finalize(state) == "final_deliverable"
