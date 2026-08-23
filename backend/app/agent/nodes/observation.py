"""Stage 6: Observation Node (TRD Section 11.3, Table 30, Section 20.2, ADR-005)."""

import logging
import re
from typing import Any, Dict, List, Optional
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.observation")


def parse_pytest_failures(stdout: str, stderr: str) -> Dict[str, Any]:
    """
    Parse test runner stdout/stderr into a structured TestFailure object (TRD Section 20.2).
    Extracts failing test identifiers and succinct error summary for model re-planning.
    """
    combined = f"{stdout}\n{stderr}"
    
    # 1. Extract failing test names
    failing_tests: List[str] = []
    # Pattern: FAILED path/to/test.py::test_func
    matches = re.findall(r"FAILED\s+([^\s]+)", combined)
    if matches:
        failing_tests = list(dict.fromkeys(matches))  # deduplicate preserving order
    else:
        # Pattern: FAIL: test_func (module.TestClass)
        matches_alt = re.findall(r"FAIL:\s+([^\s]+)", combined)
        if matches_alt:
            failing_tests = list(dict.fromkeys(matches_alt))

    # 2. Extract error summary / assertion message
    error_summary = ""
    error_lines = re.findall(r"E\s+(.+)", combined)
    if error_lines:
        error_summary = "; ".join(line.strip() for line in error_lines[:3])
    else:
        # Check for standard Python exception traces
        exc_match = re.search(r"(\w+Error:\s+[^\n]+)", combined)
        if exc_match:
            error_summary = exc_match.group(1).strip()
        else:
            # Fallback to short summary from short test summary info or tail
            summary_match = re.search(r"=+\s+short test summary info\s+=+\n(.+)", combined)
            if summary_match:
                error_summary = summary_match.group(1).strip()
            elif stderr.strip():
                error_summary = stderr.strip()[:200]
            else:
                error_summary = "Test suite failed with non-zero exit code."

    if not failing_tests and not error_lines:
        failing_tests = ["unknown_test"]

    return {
        "failing_tests": failing_tests,
        "error_summary": error_summary,
    }


def observation_node(state: AgentState) -> Dict[str, Any]:
    """Observation node: normalizes raw result into a structured ObservationRecord."""
    task_id = state["task_id"]
    task_type = state.get("task_type", "document")
    raw_res: Dict[str, Any] = state.get("_raw_execution_result") or {}
    
    broadcaster = get_event_broadcaster()
    logger.info(f"[{task_id}] Processing Observation (task_type: {task_type})")

    res_type = raw_res.get("type", "unknown")
    success = raw_res.get("success", True)
    structured_data = dict(raw_res)
    
    if res_type == "tool":
        tool_name = raw_res.get("tool_name", "tool")
        data = raw_res.get("data", {})
        
        # Coding Agent Hero Flow 2 Test Failure Mapping (TRD Section 20.2)
        if tool_name == "run_tests":
            exit_code = data.get("exit_code", 0)
            passed = data.get("passed", exit_code == 0)
            
            if not passed or exit_code != 0:
                stdout = data.get("stdout", "")
                stderr = data.get("stderr", "")
                test_failure = parse_pytest_failures(stdout, stderr)
                structured_data["test_failure"] = test_failure
                structured_data["passed"] = False
                
                content = (
                    f"Test runner failed with exit_code={exit_code}. "
                    f"Failing tests: {test_failure['failing_tests']}. "
                    f"Error: {test_failure['error_summary']}"
                )
                obs_level = "warn"  # TRD Table 30: Test failure is part of self-correction trace, not fatal crash
            else:
                content = "Test runner completed successfully. All tests passed (exit_code=0)."
                obs_level = "info"
                structured_data["passed"] = True
                
        elif success:
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
        "structured_data": structured_data,
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
