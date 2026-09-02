"""Stage 1: Task Understanding Node (TRD Section 11.3, Table 30)."""

import logging
from typing import Any, Dict
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.task_understanding")


from pathlib import Path
from backend.app.persistence.db import get_db_context
from backend.app.persistence.file_repository import FileRepository
from backend.app.persistence.task_repository import TaskRepository


def task_understanding_node(state: AgentState) -> Dict[str, Any]:
    """Parse goal + attached files into a normalized TaskRequirement; validate task_type."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    goal = state.get("goal", "").strip()

    goal_lower = goal.lower()

    # Check for coding keywords
    coding_keywords = [
        "factorial", "function", "unit test", "pytest", "docker sandbox",
        "python code", "algorithm", "self-correct", "debug", "refactor",
    ]
    is_coding_goal = any(k in goal_lower for k in coding_keywords)

    # Check for explicit document keywords
    doc_keywords = [
        "scanned document", "approval note", "read this", "compliance note",
        "compliance review", "sop compliance", "sop document", "inspection report",
        "document intelligence", "technical approval", "extract text from scan",
        "structured analysis report", "document compliance",
    ]
    is_explicit_doc_goal = any(k in goal_lower for k in doc_keywords)

    # Check for explicit vision inspection keywords
    vision_keywords = [
        "inspect this image", "corrosion", "equipment condition", "visual inspection",
        "equipment photograph", "turbine blade", "defect classification",
        "multimodal inspection", "inspection target", "inspection image", "surface condition",
    ]
    is_explicit_vision_goal = any(k in goal_lower for k in vision_keywords)

    if is_coding_goal or task_type == "coding":
        task_type = "coding"
    elif is_explicit_vision_goal and not is_explicit_doc_goal:
        task_type = "vision"
    elif task_type == "vision":
        # Keep vision unless explicitly asking for document analysis
        if is_explicit_doc_goal and not is_explicit_vision_goal:
            task_type = "document"
        else:
            task_type = "vision"
    else:
        # Default to document. Uploaded image on document task is treated as a scanned document page for OCR.
        task_type = "document"

    # Synchronize resolved task_type back to task repository if modified
    try:
        with get_db_context() as session:
            t_repo = TaskRepository(session)
            t_obj = t_repo.get_by_id(task_id)
            if t_obj and t_obj.task_type != task_type:
                t_obj.task_type = task_type
                session.commit()
    except Exception as e:
        logger.debug(f"[{task_id}] Could not sync task_type to DB: {e}")

    logger.info(f"[{task_id}] Executing Task Understanding (task_type: {task_type})")
    
    broadcaster = get_event_broadcaster()
    broadcaster.log_and_emit(
        task_id=task_id,
        node="task_understanding",
        message=f"Analyzed task goal and verified task_type '{task_type}'.",
        level="info",
    )

    return {"task_type": task_type, "goal": goal}
