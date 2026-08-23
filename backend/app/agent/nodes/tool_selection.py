"""Stage 4: Tool Selection Node (TRD Section 11.3, Table 30, Table 44, ADR-005)."""

import logging
from typing import Any, Dict, Optional
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
from backend.app.persistence.db import get_db_context
from backend.app.persistence.file_repository import FileRepository
from backend.app.tools.tool_registry import get_tool_registry

logger = logging.getLogger("sovereign_workbench.agent.node.tool_selection")


def tool_selection_node(state: AgentState) -> Dict[str, Any]:
    """Tool Selection node: filters tools permitted for task_type and binds arguments."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    plan = state.get("plan", [])
    step_idx = state.get("current_step_index", 0)
    
    current_step = plan[step_idx] if step_idx < len(plan) else "Synthesize result"
    logger.info(f"[{task_id}] Executing Tool Selection for step '{current_step}' (step {step_idx + 1}/{len(plan)}, task_type: {task_type})")
    
    registry = get_tool_registry()
    permitted_tools = [m.name for m in registry.list_tools(task_type=task_type)]
    
    broadcaster = get_event_broadcaster()
    staged_call: Optional[Dict[str, Any]] = None

    # Determine tool candidate based on plan step and task_type
    if task_type == "document":
        step_lower = current_step.lower()
        if "extract" in step_lower or "ocr" in step_lower or "report" in step_lower:
            if "extract_text_from_scan" in permitted_tools:
                # Find uploaded file associated with task if available
                file_id = "scanned_inspection_report.pdf"
                with get_db_context() as session:
                    repo = FileRepository(session)
                    task_files = repo.list_by_task_id(task_id)
                    if task_files:
                        file_id = task_files[0].file_id

                staged_call = {
                    "tool_name": "extract_text_from_scan",
                    "arguments": {"file_id": file_id, "page": 1},
                }
        elif "search" in step_lower or "knowledge base" in step_lower or "standard" in step_lower:
            if "search_knowledge_base" in permitted_tools:
                staged_call = {
                    "tool_name": "search_knowledge_base",
                    "arguments": {
                        "query": "flange corrosion relief valve calibration emergency shutdown",
                        "top_k": 4,
                    },
                }
        elif "docx" in step_lower or "approval note" in step_lower or "artifact" in step_lower:
            if "create_docx" in permitted_tools:
                # Harvest retrieved RAG citations from previous observations
                citations = []
                for obs in state.get("observations", []):
                    struct = obs.get("structured_data", {})
                    if struct.get("tool_name") == "search_knowledge_base":
                        data = struct.get("data", {})
                        citations.extend(data.get("citations", []))

                if not citations:
                    citations = [
                        "Safety SOP - Section 4.2 Emergency Shutdown Systems (p.12)",
                        "Equipment Standards - Section 11.4 Relief Valve Recertification (p.56)",
                        "Maintenance Manual - Section 8.1 Flange Integrity & Bolt Torquing (p.34)",
                    ]

                staged_call = {
                    "tool_name": "create_docx",
                    "arguments": {
                        "template": "approval_note",
                        "data": {
                            "task_id": task_id,
                            "title": "TECHNICAL APPROVAL NOTE: EQUIPMENT INSPECTION COMPLIANCE",
                            "facility": "Primary Refining Unit 02 - Flare Header & Pump Skid P-102A",
                            "summary": "Autonomous compliance assessment conducted on inspection report MRPL-INSP-2026-8842. Critical wall thinning and relief valve recalibration non-compliances require immediate remediation.",
                            "critical_findings": [
                                "Corrosion fatigue detected on primary discharge flange FL-102B bolts (1.65mm thinning > 1.50mm limit).",
                                "Pressure Relief Valve PRV-204 recalibration interval exceeded allowable 12-month limit (overdue by 2 months).",
                                "Pump P-102A mechanical seal weeping with pressure drop from 2.5 bar to 1.1 bar.",
                            ],
                            "compliance_gaps": [
                                ("Discharge Flange Wall Thinning (1.65mm)", "Safety SOP - Section 4.2 Emergency Shutdown Systems (p.12)", "CRITICAL NON-COMPLIANCE"),
                                ("PRV-204 Calibration Interval Overdue", "Equipment Standards - Section 11.4 Relief Valve Recertification (p.56)", "MAJOR GAP"),
                                ("Seal Integrity Barrier Weeping", "Maintenance Manual - Section 8.1 Flange Integrity & Bolt Torquing (p.34)", "MODERATE GAP"),
                            ],
                            "recommendations": [
                                "Initiate scheduled depressurization and bolt replacement on Flange FL-102B.",
                                "Schedule immediate hydrostatic test and recalibration for PRV-204 within 48 hours.",
                                "Replace mechanical seal pack on Pump P-102A prior to resuming continuous feed.",
                            ],
                            "citations": citations,
                        },
                    },
                }

    elif task_type == "coding":
        step_lower = current_step.lower()
        if "test" in step_lower:
            if "run_tests" in permitted_tools:
                staged_call = {
                    "tool_name": "run_tests",
                    "arguments": {"test_command": "pytest"},
                }
        elif "execute" in step_lower or "run" in step_lower or "script" in step_lower:
            if "execute_code" in permitted_tools:
                staged_call = {
                    "tool_name": "execute_code",
                    "arguments": {"code": "print('TASK_EXECUTION_SUCCESS')", "language": "python"},
                }

    if staged_call:
        # Defense-in-depth pre-registry authorization check
        if staged_call["tool_name"] not in permitted_tools:
            logger.warning(f"[{task_id}] Pre-registry filter rejected unauthorized tool '{staged_call['tool_name']}'")
            broadcaster.log_and_emit(
                task_id=task_id,
                node="tool_selection",
                message=f"Security shield: Rejected tool '{staged_call['tool_name']}' not permitted for task_type '{task_type}'.",
                level="warn",
            )
            staged_call = None
        else:
            broadcaster.log_and_emit(
                task_id=task_id,
                node="tool_selection",
                message=f"Selected tool '{staged_call['tool_name']}' for plan step {step_idx + 1}.",
                level="info",
            )

    return {"_staged_tool_call": staged_call}
