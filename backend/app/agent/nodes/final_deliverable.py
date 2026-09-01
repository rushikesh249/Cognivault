"""Stage 8: Final Deliverable Terminal Node (TRD Section 11.3, Table 30, Table 44)."""

import logging
from pathlib import Path
import shutil
from typing import Any, Dict
import uuid
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
from backend.app.core.config import settings
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
            
            # If artifact was created, verify it in database or auto-persist coding artifact
            art_repo = ArtifactRepository(session)
            if not artifact_id:
                arts = art_repo.list_by_task_id(task_id)
                if arts:
                    artifact_id = arts[-1].artifact_id
                elif status == "succeeded" and state.get("task_type") == "coding":
                    # Locate and persist generated Python source code as deliverable artifact
                    workspace_dir = Path(settings.paths.data_dir) / "sandbox" / task_id
                    if workspace_dir.exists():
                        py_files = [f for f in workspace_dir.glob("*.py") if not f.name.startswith("test_")]
                        if py_files:
                            target_py = py_files[0]
                            auto_art_id = str(uuid.uuid4())
                            outputs_dir = settings.paths.outputs_dir
                            outputs_dir.mkdir(parents=True, exist_ok=True)
                            dest_path = outputs_dir / f"{auto_art_id}_{target_py.name}"
                            shutil.copy2(target_py, dest_path)
                            
                            art_repo.create(
                                artifact_id=auto_art_id,
                                task_id=task_id,
                                kind="code",
                                title=f"Source Code Deliverable: {target_py.name}",
                                storage_path=str(dest_path.resolve()),
                                sources=[f"Sandbox Workspace: {target_py.name}"],
                            )
                            artifact_id = auto_art_id
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
