"""Unit tests for Agent State and Record Schemas (TRD Section 11.2, Table 29)."""

import pytest
from backend.app.agent.state import AgentState, ObservationRecord, ToolCallRecord


def test_tool_call_record_schema():
    """Verify ToolCallRecord schema and defaults."""
    record = ToolCallRecord(
        tool_name="read_file",
        arguments={"path": "main.py"},
        duration_ms=12,
        success=True,
    )
    assert record.tool_name == "read_file"
    assert record.arguments == {"path": "main.py"}
    assert record.duration_ms == 12
    assert record.success is True
    assert record.error is None


def test_observation_record_schema():
    """Verify ObservationRecord schema and defaults."""
    record = ObservationRecord(
        node="observation",
        content="File read successfully.",
        structured_data={"bytes": 45},
        level="info",
    )
    assert record.node == "observation"
    assert record.content == "File read successfully."
    assert record.level == "info"
    assert record.structured_data == {"bytes": 45}


def test_agent_state_type_conformance():
    """Verify AgentState TypedDict contains all fields from TRD Table 29."""
    state: AgentState = {
        "task_id": "task-test-01",
        "task_type": "document",
        "goal": "Verify compliance with safety SOP",
        "plan": ["Search knowledge base", "Verify findings"],
        "current_step_index": 0,
        "iteration": 1,
        "max_iterations": 4,
        "selected_model_id": "qwen2.5:7b-instruct",
        "tool_calls": [],
        "observations": [],
        "validation_passed": True,
        "validation_notes": None,
        "final_artifact_id": None,
        "status": "running",
        "error": None,
    }
    assert state["task_id"] == "task-test-01"
    assert state["iteration"] == 1
    assert state["max_iterations"] == 4
    assert state["status"] == "running"
