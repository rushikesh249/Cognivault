"""Hero Flow 2 Factorial Algorithm Integration Test with Real Docker Sandbox (TRD Section 20, Table 44)."""

import pytest
from backend.app.core.config import settings
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.task_repository import TaskRepository
from backend.app.sandbox.docker_runner import DockerRunner
from backend.app.services.agent_service import get_agent_service


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_factorial_hero_flow_real_docker_self_correction():
    """
    Test real Docker execution for the Factorial Algorithm Self-Correction Flow:
    1. Dedicated factorial workspace initialized with intentional defect in factorial.py
    2. Iteration 1 runs pytest in isolated Docker sandbox -> test_factorial_zero fails (assert 0 == 1)
    3. LangGraph replanning node detects failure and schedules remediation
    4. Iteration 2 executes fix script inside Docker sandbox
    5. Iteration 2 re-runs pytest inside Docker sandbox -> all tests pass (exit_code=0)
    6. Terminal node updates task record to status=succeeded on iteration 2
    """
    docker_runner = DockerRunner()
    if not docker_runner.is_available():
        pytest.skip("Docker engine is unreachable. Skipping live container integration test.")

    prompt = (
        "Implement a recursive factorial function in python with edge case verification. "
        "Inject intentional test assertion to trigger cyclic LangGraph self-correction loop in isolated Docker sandbox."
    )

    # 1. Create task in SQLite
    with get_db_context() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(
            title="Hero 2: Factorial Self-Correction Integration Test",
            task_type="coding",
            prompt=prompt,
        )
        task_id = task.task_id

    # 2. Run LangGraph via AgentService (which performs deterministic factorial workspace seeding)
    agent_service = get_agent_service()
    final_state = agent_service._run_graph_sync(task_id)

    # 3. Verify real multi-iteration self-correction cycle
    assert final_state["status"] == "succeeded", f"Expected succeeded, got {final_state.get('status')}"
    assert final_state["validation_passed"] is True
    assert final_state["iteration"] == 2, f"Expected exactly 2 iterations for self-correction, got {final_state['iteration']}"

    # 4. Verify observation records contain both failure diagnosis and subsequent pass
    observations = final_state.get("observations", [])
    assert len(observations) >= 2, "Expected multiple observations across iterations"

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

    # 5. Verify database record
    with get_db_context() as session:
        task_repo = TaskRepository(session)
        updated_task = task_repo.get_by_id(task_id)
        assert updated_task is not None
        assert updated_task.status == "succeeded"
