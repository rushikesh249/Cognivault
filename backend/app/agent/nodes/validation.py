"""Stage 7: Validation Node (TRD Section 11.3, Table 30, Table 44, ADR-005)."""

import logging
from pathlib import Path
from typing import Any, Dict
import docx

from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context

logger = logging.getLogger("sovereign_workbench.agent.node.validation")


def validation_node(state: AgentState) -> Dict[str, Any]:
    """Validation node: checks step criteria, validates deliverables, and determines loop/finalization."""
    task_id = state["task_id"]
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 4)
    observations = state.get("observations", [])

    # Check for any fatal errors in observations
    has_errors = any(obs.get("level") == "error" for obs in observations)
    validation_passed = not has_errors
    artifact_id: Any = state.get("final_artifact_id")

    # If DOCX artifact was generated, perform render-and-verify integrity check
    if validation_passed:
        with get_db_context() as session:
            repo = ArtifactRepository(session)
            arts = repo.list_by_task_id(task_id)
            if arts:
                latest_art = arts[-1]
                artifact_id = latest_art.artifact_id
                file_path = Path(latest_art.storage_path)
                
                # Check file exists and can be parsed by python-docx
                if not file_path.exists():
                    validation_passed = False
                    logger.error(f"Generated DOCX artifact missing from disk: {file_path}")
                else:
                    try:
                        doc = docx.Document(str(file_path))
                        full_doc_text = "\n".join(p.text for p in doc.paragraphs)
                        # Verify required sections exist
                        required_markers = ["Inspection", "Critical", "Compliance", "Recommendation"]
                        missing = [m for m in required_markers if m.lower() not in full_doc_text.lower()]
                        if missing:
                            validation_passed = False
                            logger.error(f"DOCX artifact missing required sections: {missing}")
                    except Exception as e:
                        validation_passed = False
                        logger.error(f"DOCX verification failed: {e}", exc_info=True)

    broadcaster = get_event_broadcaster()
    logger.info(f"[{task_id}] Validation check: passed={validation_passed} (iteration {iteration}/{max_iterations})")

    if validation_passed:
        status = "succeeded"
        validation_notes = "Plan execution and deliverable artifacts validated successfully."
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
        "final_artifact_id": artifact_id,
    }
