"""State schema and data models for LangGraph Agent Engine (TRD Section 11.2, Table 29)."""

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    """Audit record of a tool invocation within the agent loop."""
    tool_name: str = Field(..., description="Name of invoked tool")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input parameters passed to tool")
    duration_ms: int = Field(default=0, ge=0, description="Invocation duration in ms")
    success: bool = Field(default=True, description="True if tool returned success")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ObservationRecord(BaseModel):
    """Normalized observation recorded after tool or model execution."""
    node: str = Field(..., description="Node where observation was generated")
    content: str = Field(..., description="Human-readable text content or summary")
    structured_data: Optional[Dict[str, Any]] = Field(default=None, description="Parsed structured data")
    level: Literal["info", "warn", "error"] = Field(default="info", description="Severity level")


class AgentState(TypedDict):
    """Authoritative typed state passed through LangGraph nodes (TRD Table 29)."""
    task_id: str
    task_type: Literal["document", "coding", "vision"]
    goal: str
    plan: List[str]
    current_step_index: int
    iteration: int
    max_iterations: int
    selected_model_id: Optional[str]
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]
    observations: Annotated[List[Dict[str, Any]], operator.add]
    validation_passed: bool
    validation_notes: Optional[str]
    final_artifact_id: Optional[str]
    status: Literal["running", "succeeded", "failed", "failed_bounded"]
    error: Optional[str]
    _staged_tool_call: Optional[Dict[str, Any]]
    _raw_execution_result: Optional[Dict[str, Any]]
