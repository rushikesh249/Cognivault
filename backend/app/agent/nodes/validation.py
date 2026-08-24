"""Stage 7: Validation Node (TRD Section 11.3, Table 30, Table 44, Table 48, Section 20, Section 21, ADR-005)."""

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
    task_type = state.get("task_type", "document")
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 6 if task_type == "coding" else (3 if task_type == "vision" else 4))
    current_step_index = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    observations = state.get("observations", [])

    # Check for any fatal errors in observations
    has_errors = any(obs.get("level") == "error" for obs in observations)
    validation_passed = not has_errors
    artifact_id: Any = state.get("final_artifact_id")
    validation_notes: str = ""

    # Task-specific validation logic
    if task_type == "coding":
        if current_step_index < len(plan):
            if has_errors:
                validation_passed = False
                validation_notes = "Tool execution encountered fatal errors."
            else:
                validation_passed = True
                validation_notes = "Plan step executed successfully. Proceeding to next step."
        else:
            latest_test_obs = None
            for obs in reversed(observations):
                struct = obs.get("structured_data", {})
                if struct.get("tool_name") == "run_tests":
                    latest_test_obs = struct
                    break

            if latest_test_obs is not None:
                passed = latest_test_obs.get("passed", False)
                if not passed:
                    validation_passed = False
                    tf = latest_test_obs.get("test_failure", {})
                    failing = tf.get("failing_tests", [])
                    err_summary = tf.get("error_summary", "Tests failed")
                    validation_notes = f"Test failure in {failing}: {err_summary}"
                else:
                    validation_passed = True
                    validation_notes = "All test cases passed in isolated Docker sandbox."
            elif has_errors:
                validation_passed = False
                validation_notes = "Tool execution encountered fatal errors."
            else:
                validation_passed = True
                validation_notes = "Coding workflow completed successfully."

    elif task_type == "document":
        if current_step_index < len(plan):
            if has_errors:
                validation_passed = False
                validation_notes = "Tool execution encountered fatal errors."
            else:
                validation_passed = True
                validation_notes = "Plan step executed successfully. Proceeding to next step."
        else:
            if validation_passed:
                with get_db_context() as session:
                    repo = ArtifactRepository(session)
                    arts = repo.list_by_task_id(task_id)
                    if arts:
                        latest_art = arts[-1]
                        artifact_id = latest_art.artifact_id
                        file_path = Path(latest_art.storage_path)
                        
                        if not file_path.exists():
                            validation_passed = False
                            validation_notes = f"Generated DOCX artifact missing from disk: {file_path}"
                        else:
                            try:
                                doc = docx.Document(str(file_path))
                                full_doc_text = "\n".join(p.text for p in doc.paragraphs)
                                required_markers = ["Inspection", "Critical", "Compliance", "Recommendation"]
                                missing = [m for m in required_markers if m.lower() not in full_doc_text.lower()]
                                if missing:
                                    validation_passed = False
                                    validation_notes = f"DOCX artifact missing required sections: {missing}"
                                else:
                                    validation_notes = "Plan execution and deliverable artifacts validated successfully."
                            except Exception as e:
                                validation_passed = False
                                validation_notes = f"DOCX verification failed: {e}"

    elif task_type == "vision":
        # Multimodal Vision Validation (TRD ?18.1, Table 48)
        if current_step_index < len(plan):
            if has_errors:
                validation_passed = False
                validation_notes = "Vision step encountered fatal errors."
            else:
                validation_passed = True
                validation_notes = "Plan step executed successfully. Proceeding to next step."
        else:
            latest_vision_res = None
            for obs in reversed(observations):
                struct = obs.get("structured_data", {})
                if struct.get("type") == "vision" and struct.get("vision_result"):
                    latest_vision_res = struct.get("vision_result")
                    break

            if latest_vision_res:
                obs_list = latest_vision_res.get("observation", [])
                interp_list = latest_vision_res.get("interpretation", [])
                uncert_list = latest_vision_res.get("uncertainty", [])
                model_used = latest_vision_res.get("model_used")

                if not obs_list or len(obs_list) == 0:
                    validation_passed = False
                    validation_notes = "VisionResult validation failed: 'observation' array is empty."
                elif not isinstance(interp_list, list) or not isinstance(uncert_list, list):
                    validation_passed = False
                    validation_notes = "VisionResult validation failed: interpretation or uncertainty is not an array."
                elif not model_used:
                    validation_passed = False
                    validation_notes = "VisionResult validation failed: 'model_used' is missing."
                else:
                    validation_passed = True
                    validation_notes = f"Vision findings validated successfully ({len(obs_list)} observations, {len(interp_list)} interpretations, {len(uncert_list)} uncertainties)."
            elif has_errors:
                validation_passed = False
                validation_notes = "Vision workflow encountered execution errors."
            else:
                validation_passed = True
                validation_notes = "Vision workflow completed successfully."

    broadcaster = get_event_broadcaster()
    logger.info(f"[{task_id}] Validation check: passed={validation_passed} (iteration {iteration}/{max_iterations}, step {current_step_index}/{len(plan)}, task_type: {task_type})")

    if validation_passed:
        status = "succeeded" if current_step_index >= len(plan) else "running"
        if not validation_notes:
            validation_notes = "Plan execution validated successfully."
        broadcaster.log_and_emit(
            task_id=task_id,
            node="validation",
            message=f"Validation passed on iteration {iteration}/{max_iterations} (step {current_step_index}/{len(plan)}).",
            level="info",
        )
    else:
        if iteration < max_iterations:
            status = "running"
            if not validation_notes:
                validation_notes = f"Step failed on iteration {iteration}. Self-correction re-plan triggered."
            broadcaster.log_and_emit(
                task_id=task_id,
                node="validation",
                message=f"Validation failed (iteration {iteration}/{max_iterations}). Re-planning...",
                level="warn",
            )
        else:
            status = "failed_bounded"
            validation_notes = f"Max iterations ({max_iterations}) reached without successful validation. Last error: {validation_notes}"
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
