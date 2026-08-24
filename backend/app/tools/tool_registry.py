"""Tool Registry mapping tool name -> {input schema, output schema, permission set, implementation} (TRD Section 12, Component #14)."""

import logging
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from backend.app.tools.base import (
    BaseTool,
    ToolContext,
    ToolError,
    ToolMetadata,
    ToolPermissionError,
    ToolResult,
    ToolValidationError,
    UnknownToolError,
)
from backend.app.tools.code_tools import ExecuteCodeTool, RunTestsTool
from backend.app.tools.doc_tools import (
    CreateDocxTool,
    CreatePdfTool,
    CreatePptxTool,
    CreateXlsxTool,
)
from backend.app.tools.file_tools import (
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
)
from backend.app.tools.kb_tools import SearchKnowledgeBaseTool
from backend.app.tools.ocr_tools import ExtractTextFromScanTool

logger = logging.getLogger("sovereign_workbench.tools.registry")


class ToolRegistry:
    """Central registry and dispatcher for all sovereign workbench tools (TRD Table 31)."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register all 11 tools defined in TRD Table 31."""
        tools: List[BaseTool] = [
            # File tools (Component #15)
            ReadFileTool(),
            WriteFileTool(),
            ListFilesTool(),
            # RAG / Knowledge Base tool (Component #14 / #8)
            SearchKnowledgeBaseTool(),
            # OCR extraction tool (Component #12 contract)
            ExtractTextFromScanTool(),
            # Document generation tools (contracts)
            CreateDocxTool(),
            CreateXlsxTool(),
            CreatePptxTool(),
            CreatePdfTool(),
            # Code execution and testing tools (contracts)
            ExecuteCodeTool(),
            RunTestsTool(),
        ]
        for tool in tools:
            self.register_tool(tool)

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        name = tool.metadata.name
        self._tools[name] = tool
        logger.debug(f"Registered tool '{name}' (allowed: {tool.metadata.allowed_task_types})")

    def get_tool(self, name: str) -> BaseTool:
        """Retrieve a registered tool by name, raising UnknownToolError if not found."""
        if name not in self._tools:
            raise UnknownToolError(f"Unknown tool '{name}'. Available tools: {sorted(list(self._tools.keys()))}")
        return self._tools[name]

    def list_tools(self, task_type: Optional[str] = None) -> List[ToolMetadata]:
        """List metadata for all tools, optionally filtered by permitted task_type."""
        if task_type is None:
            return [t.metadata for t in self._tools.values()]
        return [
            t.metadata
            for t in self._tools.values()
            if task_type in t.metadata.allowed_task_types
        ]

    def count(self) -> int:
        """Total number of registered tools."""
        return len(self._tools)

    def invoke(self, name: str, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Validate, permission-check, and dispatch a tool invocation (TRD Section 12).
        
        Enforces:
        1. Tool existence (raises UnknownToolError before execution)
        2. Task-type permissions (raises ToolPermissionError before execution)
        3. Input schema validation (raises ToolValidationError before execution)
        4. Tool execution within isolated context
        5. Output schema validation
        """
        # 1. Existence check
        if name not in self._tools:
            logger.warning(f"Rejected invocation of unknown tool '{name}' for task '{ctx.task_id}'")
            raise UnknownToolError(f"Unknown tool '{name}'. Tool is not registered.")

        tool = self._tools[name]
        meta = tool.metadata

        # 2. Permission check per task_type
        if ctx.task_type not in meta.allowed_task_types:
            logger.warning(
                f"Permission denied: Tool '{name}' is not allowed for task_type '{ctx.task_type}' "
                f"(Allowed: {meta.allowed_task_types})"
            )
            raise ToolPermissionError(
                f"Permission denied: Tool '{name}' is disallowed for task_type '{ctx.task_type}'. "
                f"Allowed task types: {meta.allowed_task_types}"
            )

        # 3. Input schema validation
        try:
            validated_input = meta.input_schema.model_validate(args or {})
        except ValidationError as ve:
            logger.warning(f"Input validation error for tool '{name}': {ve}")
            raise ToolValidationError(f"Invalid input arguments for tool '{name}': {ve}") from ve

        # 4. Tool execution
        logger.info(f"Invoking tool '{name}' for task '{ctx.task_id}' (task_type: {ctx.task_type})")
        try:
            raw_output = tool.execute(validated_input, ctx)
        except ToolError:
            # Re-raise explicit tool and security errors directly
            raise
        except Exception as e:
            logger.error(f"Execution failure inside tool '{name}': {e}", exc_info=True)
            raise ToolError(f"Tool '{name}' execution failed: {e}") from e

        # 5. Output schema validation
        try:
            if isinstance(raw_output, meta.output_schema):
                validated_output = raw_output
            else:
                validated_output = meta.output_schema.model_validate(raw_output)
        except ValidationError as ve:
            logger.error(f"Output validation error for tool '{name}': {ve}")
            raise ToolValidationError(f"Tool '{name}' returned invalid output structure: {ve}") from ve

        return ToolResult(
            success=True,
            data=validated_output.model_dump(),
            error=None,
        )


# Global singleton instance
_global_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Retrieve or initialize the global ToolRegistry singleton."""
    global _global_tool_registry
    if _global_tool_registry is None:
        _global_tool_registry = ToolRegistry()
    return _global_tool_registry
