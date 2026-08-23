"""Code Execution and Test Runner Tool Contracts (TRD Section 12, Table 31, ADR-008).

SECURITY NOTICE: In Phase 5, these tools provide typed schema validation and contract enforcement.
Direct host execution is strictly prohibited under all conditions.
Real isolated execution in the Docker sandbox container is implemented exclusively in Phase 6.
"""

import logging
from pydantic import BaseModel, Field

from backend.app.tools.base import BaseTool, ToolContext, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.code")


# ==============================================================================
# 1. execute_code
# ==============================================================================

class ExecuteCodeInput(BaseModel):
    language: str = Field(..., description="Target programming language (e.g. python)")
    code: str = Field(..., min_length=1, description="Source code to execute in sandbox")


class ExecuteCodeOutput(BaseModel):
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    exit_code: int = Field(default=0, description="Process exit code")


class ExecuteCodeTool(BaseTool):
    """Tool contract for running code in isolated Docker sandbox (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="execute_code",
            purpose="Run code in the Docker sandbox.",
            input_schema=ExecuteCodeInput,
            output_schema=ExecuteCodeOutput,
            allowed_task_types=["coding"],
            timeout_s=30.0,
            fs_boundary="sandbox container only",
            network="none (no network)",
        )

    def execute(self, input_data: ExecuteCodeInput, ctx: ToolContext) -> ExecuteCodeOutput:
        # Phase 5 typed scaffold: strictly non-executing (Docker sandbox is Phase 6)
        logger.info(f"execute_code contract called for task '{ctx.task_id}' (language: {input_data.language})")
        return ExecuteCodeOutput(
            stdout="[Phase 5 Typed Stub: Docker sandbox container execution deferred to Phase 6]",
            stderr="",
            exit_code=0,
        )


# ==============================================================================
# 2. run_tests
# ==============================================================================

class RunTestsInput(BaseModel):
    test_command: str = Field(..., min_length=1, description="Test execution command (e.g. pytest)")


class RunTestsOutput(BaseModel):
    stdout: str = Field(default="", description="Test runner standard output")
    stderr: str = Field(default="", description="Test runner standard error")
    exit_code: int = Field(default=0, description="Test runner exit code")
    passed: bool = Field(default=True, description="True if all tests passed")


class RunTestsTool(BaseTool):
    """Tool contract for running tests in isolated Docker sandbox (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="run_tests",
            purpose="Run a test command in the same sandbox.",
            input_schema=RunTestsInput,
            output_schema=RunTestsOutput,
            allowed_task_types=["coding"],
            timeout_s=30.0,
            fs_boundary="sandbox container only",
            network="none (no network)",
        )

    def execute(self, input_data: RunTestsInput, ctx: ToolContext) -> RunTestsOutput:
        # Phase 5 typed scaffold: strictly non-executing (Docker sandbox is Phase 6)
        logger.info(f"run_tests contract called for task '{ctx.task_id}' (cmd: {input_data.test_command})")
        return RunTestsOutput(
            stdout="[Phase 5 Typed Stub: Docker sandbox container test execution deferred to Phase 6]",
            stderr="",
            exit_code=0,
            passed=True,
        )
