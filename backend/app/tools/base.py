"""Base abstractions, context, result models, and exception hierarchy for Tool Layer (TRD Section 12, Table 31)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ConfigDict


class ToolError(Exception):
    """Base exception for all tool layer errors."""
    pass


class ToolPermissionError(ToolError):
    """Raised when a task_type attempts to invoke a tool outside its permitted toolset."""
    pass


class ToolValidationError(ToolError):
    """Raised when tool input or output fails schema validation."""
    pass


class UnknownToolError(ToolError):
    """Raised when an unmapped or unknown tool name is invoked."""
    pass


class PathEscapeError(ToolError, PermissionError):
    """Raised when a filesystem tool attempts to access a path outside the task workspace sandbox."""
    pass


@dataclass
class ToolContext:
    """Execution context provided to tools during invocation."""
    task_id: str
    task_type: str  # Literal['document', 'coding', 'vision']
    workspace_dir: Optional[Path] = None


class ToolMetadata(BaseModel):
    """Metadata describing a registered tool per TRD Table 31."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    purpose: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    allowed_task_types: List[str]
    timeout_s: float
    fs_boundary: str
    network: str


class ToolResult(BaseModel):
    """Standardized result returned by ToolRegistry.invoke."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Abstract base class for all sovereign workbench tools."""

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Tool registration metadata and schemas."""
        pass

    @abstractmethod
    def execute(self, input_data: BaseModel, ctx: ToolContext) -> BaseModel:
        """Execute the tool logic and return a validated output model."""
        pass
