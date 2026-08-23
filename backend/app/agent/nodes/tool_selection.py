"""Stage 4: Tool Selection Node (TRD Section 11.3, Table 30, ADR-005)."""

import logging
from typing import Any, Dict, Optional
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
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
        if "knowledge base" in current_step.lower() or "search" in current_step.lower():
            if "search_knowledge_base" in permitted_tools:
                staged_call = {
                    "tool_name": "search_knowledge_base",
                    "arguments": {"query": state.get("goal", "compliance standard"), "top_k": 3},
                }
    elif task_type == "coding":
        if "test" in current_step.lower():
            if "run_tests" in permitted_tools:
                staged_call = {
                    "tool_name": "run_tests",
                    "arguments": {"test_command": "pytest"},
                }
        elif "execute" in current_step.lower() or "run" in current_step.lower() or "script" in current_step.lower():
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
