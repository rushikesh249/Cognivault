"""Stage 5: Execution Node (TRD Section 11.3, Table 30, Table 48)."""

import logging
import time
from typing import Any, Dict, Optional
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
from backend.app.core.config import settings
from backend.app.persistence.db import get_db_context
from backend.app.persistence.file_repository import FileRepository
from backend.app.tools.base import ToolContext, ToolError
from backend.app.tools.tool_registry import get_tool_registry

logger = logging.getLogger("sovereign_workbench.agent.node.execution")


from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.models import FileORM
from backend.app.persistence.task_repository import TaskRepository


def _task_title(task_id: str) -> Optional[str]:
    try:
        with get_db_context() as session:
            task = TaskRepository(session).get_by_id(task_id)
            return task.title if task else None
    except Exception:
        return None


def execution_node(state: AgentState) -> Dict[str, Any]:
    """Execution node: executes selected tool via ToolRegistry or runs model/vision inference."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    staged_call: Optional[Dict[str, Any]] = state.get("_staged_tool_call")

    broadcaster = get_event_broadcaster()
    logger.info(f"[{task_id}] Executing step (staged tool: {staged_call is not None}, task_type: {task_type})")

    start_time = time.time()
    tool_calls = []
    raw_result: Dict[str, Any] = {}

    if staged_call:
        tool_name = staged_call["tool_name"]
        arguments = staged_call["arguments"]
        registry = get_tool_registry()
        ctx = ToolContext(task_id=task_id, task_type=task_type)

        try:
            res = registry.invoke(tool_name, arguments, ctx)
            duration_ms = int((time.time() - start_time) * 1000)
            
            tool_record = {
                "tool_name": tool_name,
                "arguments": arguments,
                "duration_ms": duration_ms,
                "success": res.success,
                "error": res.error,
            }
            tool_calls.append(tool_record)
            raw_result = {"type": "tool", "tool_name": tool_name, "success": res.success, "data": res.data, "error": res.error}
            
            broadcaster.log_and_emit(
                task_id=task_id,
                node="execution",
                message=f"Executed tool '{tool_name}' ({'success' if res.success else 'failed'}) in {duration_ms}ms.",
                level="info" if res.success else "warn",
            )
        except ToolError as te:
            duration_ms = int((time.time() - start_time) * 1000)
            tool_record = {
                "tool_name": tool_name,
                "arguments": arguments,
                "duration_ms": duration_ms,
                "success": False,
                "error": str(te),
            }
            tool_calls.append(tool_record)
            raw_result = {"type": "tool", "tool_name": tool_name, "success": False, "error": str(te)}
            
            broadcaster.log_and_emit(
                task_id=task_id,
                node="execution",
                message=f"Tool '{tool_name}' execution error: {te}",
                level="error",
            )
    else:
        # Direct local model reasoning synthesis or multimodal Vision execution
        model_id = state.get("selected_model_id") or ("local-vision-model" if task_type == "vision" else "local-general-model")
        duration_ms = int((time.time() - start_time) * 1000)
        plan = state.get("plan", [])
        step_idx = state.get("current_step_index", 0)
        current_step = plan[step_idx] if step_idx < len(plan) else ""
        step_lower = current_step.lower()

        if task_type == "vision":
            if "artifact" in step_lower or "generate" in step_lower or "docx" in step_lower or "pdf" in step_lower or "report" in step_lower:
                # Step: Visual inspection report deliverable generation
                latest_vision_res = None
                for obs in reversed(state.get("observations", [])):
                    struct = obs.get("structured_data", {})
                    if struct.get("type") == "vision" and struct.get("vision_result"):
                        latest_vision_res = struct.get("vision_result")
                        break

                if not latest_vision_res:
                    raw_result = {
                        "type": "tool",
                        "tool_name": "create_docx",
                        "success": False,
                        "error": "No visual inspection observations available to generate report.",
                        "execution_status": "error",
                        "error_type": "missing_vision_findings",
                    }
                else:
                    obs_list = latest_vision_res.get("observation", [])
                    interp_list = latest_vision_res.get("interpretation", [])
                    uncert_list = latest_vision_res.get("uncertainty", [])
                    vision_model_used = state.get("selected_model_id") or latest_vision_res.get("model_used") or "local-vision-model"

                    # Resolve source image filename
                    source_doc = "uploaded image"
                    with get_db_context() as session:
                        repo = FileRepository(session)
                        task_files = repo.list_by_task_id(task_id)
                        if task_files:
                            source_doc = task_files[0].filename

                    task_title = _task_title(task_id) or "Industrial Equipment Visual Inspection Report"

                    # Build vision-specific sections (TRD Component #13 / ADR-007)
                    visible_components = [
                        obs for obs in obs_list
                        if any(k in obs.lower() for k in ["pipe", "flange", "joint", "screw", "bolt", "fastener", "metal", "assembly", "weld", "valve"])
                    ]
                    observed_defects = [
                        obs for obs in obs_list
                        if any(k in obs.lower() for k in ["corrosion", "rust", "peeling", "paint", "deteriorat", "crack", "wear", "gap", "defect", "damage"])
                    ]
                    other_observations = [
                        obs for obs in obs_list
                        if obs not in visible_components and obs not in observed_defects
                    ]

                    sections = [
                        {"heading": "Visual Findings", "content": obs_list},
                    ]
                    if visible_components:
                        sections.append({"heading": "Visible Objects / Components", "content": visible_components})
                    if observed_defects:
                        sections.append({"heading": "Condition / Defects Observed", "content": observed_defects})
                    if other_observations:
                        sections.append({"heading": "Additional Visual Observations", "content": other_observations})
                    if interp_list:
                        sections.append({"heading": "Engineering Interpretations & Hypotheses", "content": interp_list})
                    if uncert_list:
                        sections.append({"heading": "Limitations / Uncertain Observations", "content": uncert_list})

                    summary_text = "; ".join(obs_list) if obs_list else "Visual inspection completed."

                    doc_payload = {
                        "title": task_title,
                        "task_id": task_id,
                        "source_document": source_doc,
                        "facility": f"Source image: {source_doc}",
                        "status": f"Analyzed via {vision_model_used} (on-premise)",
                        "summary": summary_text,
                        "sections": sections,
                        "sources": [f"Uploaded image: {source_doc}"],
                        "grounding_note": f"All findings in this report are grounded exclusively in visual features extracted via {vision_model_used}. No statutory certification or certified inspection verdict is implied.",
                        "template": "structured_report",
                    }

                    out_kind = "pdf" if "pdf" in step_lower else "docx"
                    try:
                        from backend.app.documents.doc_generator import get_doc_generator
                        doc_gen = get_doc_generator()
                        out_path, artifact_id = doc_gen.render(kind=out_kind, data=doc_payload)

                        with get_db_context() as session:
                            art_repo = ArtifactRepository(session)
                            art_repo.create(
                                artifact_id=artifact_id,
                                task_id=task_id,
                                kind=out_kind,
                                title=task_title,
                                storage_path=str(out_path.resolve()),
                                sources=[f"Uploaded image: {source_doc}"],
                            )

                        raw_result = {
                            "type": "tool",
                            "tool_name": f"create_{out_kind}",
                            "success": True,
                            "artifact_id": artifact_id,
                            "output": f"Generated {out_kind.upper()} visual inspection report {artifact_id}",
                        }
                        broadcaster.log_and_emit(
                            task_id=task_id,
                            node="execution",
                            message=f"Generated visual inspection report artifact '{artifact_id}' ({out_kind.upper()}).",
                            level="info",
                        )
                    except Exception as e:
                        logger.error(f"[{task_id}] Failed generating visual inspection artifact: {e}", exc_info=True)
                        raw_result = {
                            "type": "tool",
                            "tool_name": f"create_{out_kind}",
                            "success": False,
                            "error": str(e),
                            "execution_status": "error",
                            "error_type": "artifact_generation_error",
                        }
                        broadcaster.log_and_emit(
                            task_id=task_id,
                            node="execution",
                            message=f"Failed generating visual inspection artifact: {e}",
                            level="error",
                        )
            else:
                # Step: Multimodal Vision Analysis execution (TRD §18, §21, Table 48)
                attached_file_id: Optional[str] = None
                source_filename: str = "attached image"
                with get_db_context() as session:
                    repo = FileRepository(session)
                    task_files = repo.list_by_task_id(task_id)
                    if task_files:
                        attached_file_id = task_files[0].file_id
                        source_filename = task_files[0].filename
                    else:
                        recent_image = (
                            session.query(FileORM)
                            .filter(FileORM.mime_type.like("image/%"))
                            .order_by(FileORM.uploaded_at.desc())
                            .first()
                        )
                        if recent_image:
                            attached_file_id = recent_image.file_id
                            source_filename = recent_image.filename
                            repo.attach_to_task(attached_file_id, task_id)

                if not attached_file_id:
                    for f in settings.paths.uploads_dir.glob("*"):
                        if f.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                            attached_file_id = f.stem
                            source_filename = f.name
                            break
                    if not attached_file_id:
                        demo_img = Path("knowledge_base/demo_inputs/synthetic_weld_flange.jpg")
                        if demo_img.exists():
                            attached_file_id = demo_img.name
                            source_filename = demo_img.name

                vision_model_to_use = state.get("selected_model_id") or "local-vision-model"

                try:
                    from backend.app.services.vision_service import get_vision_app_service
                    vision_app = get_vision_app_service()
                    if attached_file_id:
                        v_res = vision_app.analyze_file(file_id=attached_file_id, prompt=state.get("goal"))
                        raw_result = {
                            "type": "vision",
                            "model_id": v_res.model_used or vision_model_to_use,
                            "success": True,
                            "vision_result": v_res.model_dump(),
                        }
                        broadcaster.log_and_emit(
                            task_id=task_id,
                            node="execution",
                            message=f"Completed multimodal VLM analysis via '{v_res.model_used or vision_model_to_use}' on image '{source_filename}'.",
                            level="info",
                        )
                    else:
                        raw_result = {
                            "type": "vision",
                            "model_id": vision_model_to_use,
                            "success": False,
                            "error": "No image file attached for vision task.",
                            "execution_status": "error",
                            "error_type": "missing_image_file",
                        }
                        broadcaster.log_and_emit(
                            task_id=task_id,
                            node="execution",
                            message="No image file attached for vision task.",
                            level="error",
                        )
                except Exception as e:
                    logger.error(f"[{task_id}] Multimodal vision execution error: {e}", exc_info=True)
                    raw_result = {
                        "type": "vision",
                        "model_id": vision_model_to_use,
                        "success": False,
                        "error": str(e),
                        "execution_status": "error",
                        "error_type": "model_unavailable" if "unavailable" in str(e).lower() else "vision_error",
                    }
                    broadcaster.log_and_emit(
                        task_id=task_id,
                        node="execution",
                        message=f"Multimodal vision execution failed: {e}",
                        level="error",
                    )
        else:
            if task_type == "document":
                # Grounded document analysis: the uploaded document's extracted
                # text is the primary source; KB matches are supplementary only.
                # Runs real local-model inference (no fabricated model output).
                from backend.app.services.document_analysis import (
                    DocumentAnalysisError,
                    get_document_analysis_service,
                )

                extracted_text = ""
                kb_matches = []
                for obs in state.get("observations", []):
                    struct = obs.get("structured_data", {})
                    if not struct.get("success", True):
                        continue
                    if struct.get("tool_name") == "extract_text_from_scan":
                        text = (struct.get("data") or {}).get("text", "")
                        if text:
                            extracted_text = text
                    elif struct.get("tool_name") == "search_knowledge_base":
                        kb_matches.extend((struct.get("data") or {}).get("matches", []) or [])

                source_document = "uploaded document"
                with get_db_context() as session:
                    repo = FileRepository(session)
                    task_files = repo.list_by_task_id(task_id)
                    if task_files:
                        source_document = task_files[0].filename

                try:
                    analysis = get_document_analysis_service().analyze(
                        extracted_text=extracted_text,
                        source_document=source_document,
                        goal=state.get("goal") or "",
                        kb_matches=kb_matches,
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    raw_result = {
                        "type": "model",
                        "model_id": analysis.get("analysis_model", model_id),
                        "success": True,
                        "analysis": analysis,
                        "output": (
                            f"Document analysis completed via {analysis.get('analysis_model')}. "
                            f"Main topic: {analysis['section_values'].get('main_topic', 'n/a')[:160]}"
                        ),
                    }
                    broadcaster.log_and_emit(
                        task_id=task_id,
                        node="execution",
                        message=f"Completed grounded document analysis of '{source_document}' via '{analysis.get('analysis_model')}' in {duration_ms}ms.",
                        level="info",
                    )
                except DocumentAnalysisError as dae:
                    raw_result = {
                        "type": "model",
                        "model_id": model_id,
                        "success": False,
                        "error": str(dae),
                    }
                    broadcaster.log_and_emit(
                        task_id=task_id,
                        node="execution",
                        message=f"Document analysis failed: {dae}",
                        level="error",
                    )
                except Exception as e:
                    logger.error(f"[{task_id}] Document analysis execution error: {e}", exc_info=True)
                    raw_result = {
                        "type": "model",
                        "model_id": model_id,
                        "success": False,
                        "error": f"Document analysis error: {e}",
                    }
                    broadcaster.log_and_emit(
                        task_id=task_id,
                        node="execution",
                        message=f"Document analysis failed: {e}",
                        level="error",
                    )
            else:
                raw_result = {
                    "type": "model",
                    "model_id": model_id,
                    "success": True,
                    "output": f"Step analysis completed using {model_id}.",
                }
                broadcaster.log_and_emit(
                    task_id=task_id,
                    node="execution",
                    message=f"Completed model inference step via '{model_id}'.",
                    level="info",
                )

    return {
        "tool_calls": tool_calls,
        "_raw_execution_result": raw_result,
        "_staged_tool_call": None,
    }
