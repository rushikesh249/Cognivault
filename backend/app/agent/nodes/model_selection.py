"""Stage 3: Model Selection Node (TRD Section 11.3, Table 30, ADR-004)."""

import logging
from typing import Any, Dict
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
from backend.app.models.exceptions import ModelUnavailable
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.router import ModelRouter

logger = logging.getLogger("sovereign_workbench.agent.node.model_selection")


def model_selection_node(state: AgentState) -> Dict[str, Any]:
    """Model Selection node: selects optimal local model via ModelRouter."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    registry = ModelRegistry()

    logger.info(f"[{task_id}] Executing Model Selection for task_type '{task_type}'")
    broadcaster = get_event_broadcaster()
    selected_id = None

    try:
        selected_id = ModelRouter.select_for_task_type(
            task_type=task_type,
            registry=registry,
            enforce_availability=False,
        )
        broadcaster.log_and_emit(
            task_id=task_id,
            node="model_selection",
            message=f"Model Router selected local model '{selected_id}' for task_type '{task_type}'.",
            level="info",
        )
    except ModelUnavailable as e:
        logger.warning(f"[{task_id}] No suitable model available for task_type '{task_type}': {e}")
        broadcaster.log_and_emit(
            task_id=task_id,
            node="model_selection",
            message=f"Model selection warning: {e}",
            level="warn",
        )

    return {"selected_model_id": selected_id}
