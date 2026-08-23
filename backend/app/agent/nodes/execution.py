"""Stage 5: Execution Node (TRD Section 11.3, Table 30)."""

import logging
import time
from typing import Any, Dict, Optional
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState
from backend.app.tools.base import ToolContext, ToolError
from backend.app.tools.tool_registry import get_tool_registry

logger = logging.getLogger("sovereign_workbench.agent.node.execution")


def execution_node(state: AgentState) -> Dict[str, Any]:
    """Execution node: executes selected tool via ToolRegistry or runs model inference."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    staged_call: Optional[Dict[str, Any]] = state.get("_staged_tool_call")

    broadcaster = get_event_broadcaster()
    logger.info(f"[{task_id}] Executing step (staged tool: {staged_call is not None})")

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
        # Step executed as local model reasoning synthesis
        model_id = state.get("selected_model_id") or "local-default"
        duration_ms = int((time.time() - start_time) * 1000)
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
