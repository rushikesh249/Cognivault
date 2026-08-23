"""Stage 7: Validation Node (TRD Section 11.3, Table 30, ADR-005)."""

import logging
from typing import Any, Dict
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.validation")


def validation_node(state: AgentState) -> Dict[str, Any]:
    """Validation node: checks step criteria and determines loop or finalization."""
    task_id = state["task_id"]
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 4)
    observations = state.get("observations", [])

    # Check for any fatal errors in observations
    has_errors = any(obs.get("level") == "error" for obs in observations)
    validation_passed = not has_errors

    broadcaster = get_event_broadcaster()
    logger.info(f"[{task_id}] Validation check: passed={validation_passed} (iteration {iteration}/{max_iterations})")

    if validation_passed:
        status = "succeeded"
        validation_notes = "Plan execution validated successfully."
        broadcaster.log_and_emit(
            task_id=task_id,
            node="validation",
            message=f"Validation passed on iteration {iteration}/{max_iterations}.",
            level="info",
        )
    else:
        if iteration < max_iterations:
            status = "running"
            validation_notes = f"Step failed on iteration {iteration}. Self-correction re-plan triggered."
            broadcaster.log_and_emit(
                task_id=task_id,
                node="validation",
                message=f"Validation failed (iteration {iteration}/{max_iterations}). Re-planning...",
                level="warn",
            )
        else:
            status = "failed_bounded"
            validation_notes = f"Max iterations ({max_iterations}) reached without successful validation."
            broadcaster.log_and_emit(
                task_id=task_id,
                node="validation",
                message=f"Iteration limit reached ({max_iterations}/{max_iterations}). Terminating with status=failed_bounded.",
                level="error",
            )

    return {
        "validation_passed": validation_passed,
        "status": status,
        "validation_notes": validation_notes,
    }
