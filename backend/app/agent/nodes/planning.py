"""Stage 2: Planning Node (TRD Section 11.3, Table 30, Table 44, Section 20, Section 21, ADR-005)."""

import logging
from typing import Any, Dict, List
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.planning")


def generate_default_plan(task_type: str, goal: str) -> List[str]:
    """Generate default execution plan based on task_type and goal (TRD Table 44, Table 48)."""
    if task_type == "document":
        goal_lower = (goal or "").lower()
        if "xlsx" in goal_lower or "excel" in goal_lower or "spreadsheet" in goal_lower:
            format_step = "Generate technical summary XLSX artifact"
        elif "pptx" in goal_lower or "presentation" in goal_lower or "deck" in goal_lower or "slides" in goal_lower:
            format_step = "Generate management summary deck PPTX artifact"
        elif "pdf" in goal_lower:
            format_step = "Generate technical report PDF artifact"
        elif "approval note" in goal_lower:
            format_step = "Generate technical Approval Note DOCX artifact"
        else:
            format_step = "Generate structured analysis report DOCX artifact"

        # Grounded document pipeline: the uploaded document is extracted first,
        # the knowledge base is searched with document-derived queries only,
        # and the local model analyzes the extracted text before rendering.
        return [
            "Extract text from the uploaded document",
            "Search knowledge base for supporting context",
            "Analyze the extracted document content with the local model",
            format_step,
        ]
    elif task_type == "coding":
        goal_lower = (goal or "").lower()
        if "test" in goal_lower or "fix" in goal_lower or "defect" in goal_lower or "bug" in goal_lower:
            return ["Execute test suite to detect failures"]
        return ["Execute solution script in sandbox"]
    elif task_type == "vision":
        goal_lower = (goal or "").lower()
        if "pdf" in goal_lower:
            return [
                "Analyze inspection image with local vision-language model",
                "Generate visual inspection report PDF artifact",
            ]
        elif "docx" in goal_lower or "report" in goal_lower or "artifact" in goal_lower or "document" in goal_lower:
            return [
                "Analyze inspection image with local vision-language model",
                "Generate visual inspection report DOCX artifact",
            ]
        return [
            "Analyze inspection image with local vision-language model",
            "Extract structured visual observations, interpretations, and uncertainties",
        ]
    return ["Analyze requirements and synthesize deliverable"]


def planning_node(state: AgentState) -> Dict[str, Any]:
    """Planning node: Increments iteration counter and generates ordered execution plan."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    goal = state.get("goal", "")
    
    # Invariant: iteration counter increments ONLY when entering Planning
    current_iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", 6 if task_type == "coding" else (3 if task_type == "vision" else 4))

    logger.info(f"[{task_id}] Executing Planning (iteration {current_iteration}/{max_iterations}, task_type: {task_type})")

    # If this is a re-plan after test/validation failure, formulate targeted remediation plan
    if current_iteration > 1 and state.get("validation_notes"):
        failure_note = state["validation_notes"]
        if task_type == "coding":
            plan = [
                "Generate and apply corrected code to sandbox workspace",
                "Re-run test suite verification",
            ]
        elif task_type == "vision":
            plan = [
                "Re-evaluate inspection image with adjusted vision prompt",
                "Extract structured visual observations, interpretations, and uncertainties",
            ]
        else:
            plan = [
                f"Address failure: {failure_note}",
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
