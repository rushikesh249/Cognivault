"""Stage 8: Final Deliverable Terminal Node (TRD Section 11.3, Table 30, Table 44)."""

import logging
from typing import Any, Dict
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context
from backend.app.persistence.task_repository import TaskRepository

logger = logging.getLogger("sovereign_workbench.agent.node.final_deliverable")


def final_deliverable_node(state: AgentState) -> Dict[str, Any]:
    """Final Deliverable node: persists terminal status in DB and emits final completion event."""
    task_id = state["task_id"]
    status = state.get("status", "succeeded")
    model_used = state.get("selected_model_id")
    artifact_id = state.get("final_artifact_id")

    logger.info(f"[{task_id}] Finalizing Deliverable with status '{status}' (artifact: {artifact_id})")
    
    # Synchronously update task status in database
    try:
        with get_db_context() as session:
            repo = TaskRepository(session)
            repo.update_status(
                task_id=task_id,
                status=status,
                model_used=model_used,
            )
            
            # If artifact was created, verify it in database
            if not artifact_id:
                art_repo = ArtifactRepository(session)
                arts = art_repo.list_by_task_id(task_id)
                if arts:
                    artifact_id = arts[-1].artifact_id
    except Exception as e:
        logger.error(f"[{task_id}] Failed to persist final task status: {e}", exc_info=True)

    broadcaster = get_event_broadcaster()
    broadcaster.log_and_emit(
        task_id=task_id,
        node="final_deliverable",
        message=f"Agent workflow complete with status='{status}'." + (f" Artifact: {artifact_id}" if artifact_id else ""),
        level="info" if status == "succeeded" else "warn",
    )

    return {"status": status, "final_artifact_id": artifact_id}
