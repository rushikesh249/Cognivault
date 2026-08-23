"""Stage 2: Planning Node (TRD Section 11.3, Table 30, Table 44, ADR-005)."""

import logging
from typing import Any, Dict, List
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.planning")


def generate_default_plan(task_type: str, goal: str) -> List[str]:
    """Generate default execution plan based on task_type and goal (TRD Table 44)."""
    if task_type == "document":
        return [
            "Extract findings and anomalies from inspection report",
            "Search safety standards and guidelines in knowledge base",
            "Evaluate compliance gaps against safety clauses",
            "Generate technical Approval Note DOCX artifact",
        ]
    elif task_type == "coding":
        return [
            "Generate solution script",
            "Execute generated script in sandbox",
            "Run test suite verification",
        ]
    elif task_type == "vision":
        return [
            "Inspect input visual features",
            "Extract visual metrics and synthesize analysis",
        ]
    return ["Analyze requirements and synthesize deliverable"]


def planning_node(state: AgentState) -> Dict[str, Any]:
    """Planning node: Increments iteration counter and generates ordered execution plan."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    goal = state.get("goal", "")
    
    # Invariant: iteration counter increments ONLY when entering Planning
    current_iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", 4)

    logger.info(f"[{task_id}] Executing Planning (iteration {current_iteration}/{max_iterations})")

    # If this is a re-plan after validation failure, consider validation notes
    if current_iteration > 1 and state.get("validation_notes"):
        plan = [
            f"Address failure: {state['validation_notes']}",
            "Re-execute corrected step",
            "Re-validate results",
        ]
    else:
        plan = generate_default_plan(task_type, goal)

    broadcaster = get_event_broadcaster()
    broadcaster.log_and_emit(
        task_id=task_id,
        node="planning",
        message=f"Formulated plan with {len(plan)} sub-steps (iteration {current_iteration}/{max_iterations}).",
        level="info",
    )

    return {
        "iteration": current_iteration,
        "plan": plan,
        "current_step_index": 0,
    }
