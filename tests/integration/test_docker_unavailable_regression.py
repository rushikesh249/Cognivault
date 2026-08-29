"""Regression Test: Docker infrastructure failure must never become a successful test result.

Bug scenario (manual E2E verification):
    [execution]  Tool 'run_tests' execution error: 503 ServiceUnavailable: Docker daemon ...
    [observation] Observed outcome: Test runner completed successfully. All tests passed (exit_code=0).
    [final_deliverable] status='succeeded'   <- INCORRECT

Correct semantics:
    Docker execution error -> observation = infrastructure error (no exit code)
    -> validation fails with status='failed' -> final status 'failed', never 'succeeded'.

Mocking is applied ONLY at the Docker infrastructure boundary (DockerRunner.run),
exactly as the existing isolation test does. The real Docker factorial integration
test (test_factorial_coding_flow.py) remains untouched.
"""

from unittest.mock import patch

import pytest

from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.task_repository import TaskRepository
from backend.app.sandbox.docker_runner import DockerRunner, ServiceUnavailableError
from backend.app.services.agent_service import get_agent_service


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_docker_unavailable_run_tests_never_reports_success():
    """
    Full graph run of the factorial coding task while the Docker daemon is
    unreachable (simulated at the DockerRunner boundary):

    1. run_tests raises ServiceUnavailableError (503)
    2. Observation must NOT report exit_code=0 or 'All tests passed'
    3. Validation must NOT pass
    4. No self-correction fix may be applied on top of missing pytest output
    5. Final status must be 'failed' (not 'succeeded', not 'failed_bounded')
    """
    prompt = (
        "Write a python factorial function with unit tests in Docker sandbox. "
        "If tests fail, inspect stderr and self-correct."
    )

    with get_db_context() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(
            title="Regression: Docker Unavailable Factorial Task",
            task_type="coding",
            prompt=prompt,
        )
        task_id = task.task_id

    # Simulate Docker daemon unreachable at the infrastructure boundary only
    with patch.object(
        DockerRunner,
        "run",
        side_effect=ServiceUnavailableError(
            "503 ServiceUnavailable: Docker daemon is not running or unreachable."
        ),
    ):
        final_state = get_agent_service()._run_graph_sync(task_id)

    # 1. Terminal status must be an explicit failure
    assert final_state["status"] == "failed", (
        f"Docker infrastructure failure must end as 'failed', got {final_state.get('status')}"
    )
    assert final_state["validation_passed"] is False

    # 2. No observation may claim a successful pytest run or synthesize exit_code=0
    observations = final_state.get("observations", [])
    assert observations, "Expected at least one observation record"
    for obs in observations:
        content = obs.get("content", "")
        assert "All tests passed" not in content, (
            "Docker execution error was converted into a successful test result"
        )
        sd = obs.get("structured_data", {})
        assert sd.get("passed") is not True
        if sd.get("tool_name") == "run_tests":
            data = sd.get("data") or {}
            assert data.get("exit_code") != 0, "exit_code=0 synthesized from Docker failure"

    # 3. The infrastructure error must be preserved in structured state
    run_tests_obs = [
        obs for obs in observations
        if obs.get("structured_data", {}).get("tool_name") == "run_tests"
    ]
    assert run_tests_obs, "Expected a run_tests observation"
    sd = run_tests_obs[0]["structured_data"]
    assert sd.get("execution_status") == "error"
    assert sd.get("error_type") == "docker_unavailable"
    assert "503 ServiceUnavailable" in sd.get("error_message", "")

    # 4. No correction script may have been executed (nothing to correct without pytest output)
    executed_tools = [
        obs.get("structured_data", {}).get("tool_name")
        for obs in observations
    ]
    assert "execute_code" not in executed_tools, (
        "Self-correction must not run on top of a Docker infrastructure failure"
    )

    # 5. Database record must reflect the failure
    with get_db_context() as session:
        task_repo = TaskRepository(session)
        updated_task = task_repo.get_by_id(task_id)
        assert updated_task is not None
        assert updated_task.status == "failed"
