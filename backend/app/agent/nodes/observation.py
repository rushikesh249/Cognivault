"""Stage 6: Observation Node (TRD Section 11.3, Table 30)."""

import logging
from typing import Any, Dict
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.observation")


def observation_node(state: AgentState) -> Dict[str, Any]:
    """Observation node: normalizes raw result into a structured ObservationRecord."""
    task_id = state["task_id"]
    raw_res: Dict[str, Any] = state.get("_raw_execution_result") or {}
    
    broadcaster = get_event_broadcaster()
    logger.info(f"[{task_id}] Processing Observation")

    res_type = raw_res.get("type", "unknown")
    success = raw_res.get("success", True)
    
    if res_type == "tool":
        tool_name = raw_res.get("tool_name", "tool")
        if success:
            content = f"Tool '{tool_name}' returned valid output."
            obs_level = "info"
        else:
            content = f"Tool '{tool_name}' failed: {raw_res.get('error', 'unknown error')}"
            obs_level = "error"
    else:
        content = raw_res.get("output", "Model step completed successfully.")
        obs_level = "info"

    obs_record = {
        "node": "observation",
        "content": content,
        "structured_data": raw_res,
        "level": obs_level,
    }
    
    # Advance to next step in current plan
    next_step_idx = state.get("current_step_index", 0) + 1

    broadcaster.log_and_emit(
        task_id=task_id,
        node="observation",
        message=f"Observed outcome: {content}",
        level=obs_level,
    )

    return {
        "observations": [obs_record],
        "current_step_index": next_step_idx,
        "_raw_execution_result": None,
    }
