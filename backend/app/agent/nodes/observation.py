"""Stage 6: Observation Node (TRD Section 11.3, Table 30, Section 20.2, ADR-005)."""

import logging
import re
from typing import Any, Dict, List, Optional
from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.agent.state import AgentState

logger = logging.getLogger("sovereign_workbench.agent.node.observation")


def _classify_pytest_failure(exit_code: Optional[int], combined: str) -> str:
    """
    Classify a pytest outcome into a structured failure kind so downstream
    self-correction can distinguish genuine test failures from collection,
    usage, or interruption problems (TRD Section 20.2).

    Exit codes: 0=passed, 1=tests failed, 2=interrupted/usage problem,
    4=command-line usage error, 5=no tests collected.
    """
    lower = combined.lower()
    has_error_markers = (
        re.search(r"\berrors?\b", lower) is not None
        or "importerror" in lower
        or "modulenotfounderror" in lower
        or "syntaxerror" in lower
    )
    if exit_code == 0:
        return "passed"
    if exit_code == 1:
        return "test_failure"
    # Explicit pytest exit codes take precedence over content heuristics
    if exit_code == 5:
        return "no_tests_collected"
    if exit_code == 4:
        return "usage_error"
    if exit_code == 2:
        return "collection_error" if has_error_markers else "interrupted"
    # Content-based fallback when exit code is absent or non-standard
    if has_error_markers and ("collected" in lower or "importerror" in lower or "modulenotfounderror" in lower or "syntaxerror" in lower):
        return "collection_error"
    if "no tests ran" in lower or "collected 0 items" in lower or "no tests were collected" in lower:
        return "no_tests_collected"
    return "test_failure"


def parse_pytest_failures(stdout: str, stderr: str, exit_code: Optional[int] = None) -> Dict[str, Any]:
    """
    Parse test runner stdout/stderr into a structured TestFailure object (TRD Section 20.2).
    Extracts failing test identifiers, assertion messages, and syntax/collection errors.
    When exit_code is provided, pytest exit-code semantics (0/1/2/4/5) are used to
    classify the failure so e.g. exit_code=5 is reported as a no-tests-collected
    problem rather than an unknown failing test.
    """
    combined = f"{stdout}\n{stderr}"
    failure_kind = _classify_pytest_failure(exit_code, combined)

    # 1. Extract failing test names
    failing_tests: List[str] = []
    matches = re.findall(r"FAILED\s+([^\s]+)", combined)
    if matches:
        failing_tests = list(dict.fromkeys(matches))
    else:
        matches_alt = re.findall(r"FAIL:\s+([^\s]+)", combined)
        if matches_alt:
            failing_tests = list(dict.fromkeys(matches_alt))

    # 2. Extract error summary / assertion message
    error_summary = ""
    error_lines = re.findall(r"E\s+(.+)", combined)
    if error_lines:
        error_summary = "; ".join(line.strip() for line in error_lines[:3])
    else:
        exc_match = re.search(r"((?:\w+Error|Exception):\s+[^\n]+)", combined)
        if exc_match:
            error_summary = exc_match.group(1).strip()
        else:
            summary_match = re.search(r"=+\s+short test summary info\s+=+\n(.+)", combined)
            if summary_match:
                error_summary = summary_match.group(1).strip()
            elif stderr.strip():
                error_summary = stderr.strip()[:200]
            elif "no tests ran" in combined.lower() or "collected 0 items" in combined.lower():
                error_summary = "No test cases found or collected in test suite."
            else:
                error_summary = "Test suite failed with non-zero exit code."

    if not failing_tests and not error_lines:
        if failure_kind == "no_tests_collected":
            failing_tests = ["no_tests_collected"]
        elif exc_match:
            failing_tests = [exc_match.group(1).split(":")[0].strip()]
        else:
            failing_tests = ["unknown_test"]

    # 2b. Extract collection errors (e.g. ImportError during test collection)
    collection_errors: List[str] = re.findall(r"^E\s+.*(?:Error|Exception).*", combined, re.MULTILINE)
    if not collection_errors and failure_kind in ("collection_error", "interrupted", "usage_error"):
        err_match = re.search(r"((?:\w+Error|Exception):\s+[^\n]+)", combined)
        if err_match:
            collection_errors = [err_match.group(1).strip()]

    result: Dict[str, Any] = {
        "failing_tests": failing_tests,
        "error_summary": error_summary,
        "failure_kind": failure_kind,
        "collection_errors": collection_errors[:5],
    }
    if exit_code is not None:
        result["exit_code"] = exit_code
    return result


def _classify_tool_execution_error(error_message: str) -> str:
    """
    Classify a tool execution error into an infrastructure error type so
    downstream validation can distinguish sandbox/Docker infrastructure
    failures from genuine test failures (TRD Section 20.2).
    """
    lower = (error_message or "").lower()
    if "docker" in lower or "503" in lower or "serviceunavailable" in lower:
        return "docker_unavailable"
    if "timed out" in lower or "timeout" in lower:
        return "timeout"
    return "tool_error"


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
        data = raw_res.get("data") or {}

        if not success:
            # Infrastructure/tool execution failure (e.g. Docker daemon unreachable -> 503).
            # pytest never executed, so no exit code may be synthesized and the outcome
            # must never be reported as a successful test result.
            error_message = raw_res.get("error") or "unknown tool execution error"
            error_type = _classify_tool_execution_error(error_message)
            structured_data["execution_status"] = "error"
            structured_data["error_type"] = error_type
            structured_data["error_message"] = error_message
            if tool_name == "run_tests":
                structured_data["passed"] = False
                content = (
                    f"Test runner infrastructure failure ({error_type}): {error_message}. "
                    "pytest did not execute; no test result or exit code is available."
                )
            else:
                content = f"Tool '{tool_name}' execution failed ({error_type}): {error_message}"
            obs_level = "error"

        elif tool_name == "run_tests":
            # Real pytest outcome: Docker execution succeeded and produced an exit code.
            exit_code = data.get("exit_code")
            if exit_code is None:
                # Defensive invariant: a successful run_tests invocation must always
                # carry a real pytest exit code; otherwise treat as invalid output.
                structured_data["execution_status"] = "error"
                structured_data["error_type"] = "invalid_tool_output"
                structured_data["error_message"] = "run_tests returned no pytest exit code."
                structured_data["passed"] = False
                content = "Test runner returned an invalid output: no pytest exit code present."
                obs_level = "error"
            else:
                passed = data.get("passed", exit_code == 0)

                if not passed or exit_code != 0:
                    stdout = data.get("stdout", "")
                    stderr = data.get("stderr", "")
                    test_failure = parse_pytest_failures(stdout, stderr, exit_code=exit_code)
                    structured_data["test_failure"] = test_failure
                    structured_data["passed"] = False

                    failure_kind = test_failure.get("failure_kind", "test_failure")
                    if failure_kind == "no_tests_collected":
                        content = (
                            f"Test runner reported exit_code={exit_code}: no tests were collected. "
                            "The workspace does not contain collectable test files; source/test files "
                            "must be created in the sandbox workspace before running pytest."
                        )
                    else:
                        content = (
                            f"Test runner failed with exit_code={exit_code} ({failure_kind}). "
                            f"Failing tests: {test_failure['failing_tests']}. "
                            f"Error: {test_failure['error_summary']}"
                        )
                    obs_level = "warn"
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

    elif res_type == "vision":
        # Multimodal Vision observation handling (TRD ?18.1, Table 48)
        if success:
            vr = structured_data.get("vision_result", {})
            obs_list = vr.get("observation", [])
            content = f"VLM extracted {len(obs_list)} visual observation(s): {'; '.join(obs_list[:2])}"
            obs_level = "info"
        else:
            content = f"Vision analysis failed: {structured_data.get('error', 'unknown error')}"
            obs_level = "error"

    else:
        # Model inference step (e.g. grounded document analysis). A failed model
        # step must surface as an error observation, never as silent success.
        if success:
            content = raw_res.get("output", "Model step completed successfully.")
            obs_level = "info"
        else:
            content = f"Model analysis step failed: {raw_res.get('error', 'unknown error')}"
            obs_level = "error"

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
