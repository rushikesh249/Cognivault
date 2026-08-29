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

    # Check attached files for image content
    has_image_attachment = False
    with get_db_context() as session:
        repo = FileRepository(session)
        task_files = repo.list_by_task_id(task_id)
        for f in task_files:
            fn = (f.filename or "").lower()
            mt = (f.mime_type or "").lower()
            if mt.startswith("image/") or any(fn.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                has_image_attachment = True
                break

    goal_lower = goal.lower()
    if has_image_attachment or "inspection image" in goal_lower or "equipment photograph" in goal_lower or "visual inspection" in goal_lower or "turbine blade" in goal_lower:
        if task_type != "coding":
            task_type = "vision"
            # Update DB task_type if needed
            try:
                with get_db_context() as session:
                    t_repo = TaskRepository(session)
                    t_obj = t_repo.get_by_id(task_id)
                    if t_obj and t_obj.task_type != "vision":
                        t_obj.task_type = "vision"
                        session.commit()
            except Exception:
                pass

    if task_type not in ["document", "coding", "vision"]:
        task_type = "document"

    logger.info(f"[{task_id}] Executing Task Understanding (task_type: {task_type})")
    
    broadcaster = get_event_broadcaster()
    broadcaster.log_and_emit(
        task_id=task_id,
        node="task_understanding",
        message=f"Analyzed task goal and verified task_type '{task_type}'.",
        level="info",
    )

    return {"task_type": task_type, "goal": goal}
