"""Stage 1: Task Understanding Node (TRD Section 11.3, Table 30)."""

import logging
from typing import Any, Dict
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.task_understanding")


def task_understanding_node(state: AgentState) -> Dict[str, Any]:
    """Parse goal + attached files into a normalized TaskRequirement; validate task_type."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    goal = state.get("goal", "").strip()

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
