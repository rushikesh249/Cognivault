"""Code Execution and Test Runner Tool Implementations (TRD Section 12, Section 20, Table 31, ADR-008).

Executes code and test commands in the isolated sovereign-sandbox Docker container.
Strictly adheres to:
- Zero host code execution fallback under all conditions.
- Docker daemon failure raises 503-equivalent ToolError.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from backend.app.sandbox.docker_runner import DockerRunner, ServiceUnavailableError, get_docker_runner
from backend.app.sandbox.sandbox_spec import SandboxSpec
from backend.app.tools.base import BaseTool, ToolContext, ToolError, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.code")


# ==============================================================================
# 1. execute_code
# ==============================================================================

class ExecuteCodeInput(BaseModel):
    language: str = Field(default="python", description="Target programming language (e.g. python)")
    code: str = Field(..., min_length=1, description="Source code to execute in sandbox")


class ExecuteCodeOutput(BaseModel):
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    exit_code: int = Field(default=0, description="Process exit code")


class ExecuteCodeTool(BaseTool):
    """Tool for running code in isolated Docker sandbox (TRD Table 31)."""

    def __init__(self, runner: Optional[DockerRunner] = None):
        self._runner = runner

    def _get_runner(self) -> DockerRunner:
        if self._runner is None:
            self._runner = get_docker_runner()
        return self._runner

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
        runner = self._get_runner()
        spec = SandboxSpec(
            task_id=ctx.task_id,
            code=input_data.code,
            language=input_data.language,
            timeout_s=30,
            workspace_dir=ctx.workspace_dir,
        )

        try:
            res = runner.run(spec)
            return ExecuteCodeOutput(
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
            )
        except ServiceUnavailableError as sue:
            raise ToolError(f"503 ServiceUnavailable: {sue}") from sue
        except Exception as e:
            raise ToolError(f"Code execution error: {e}") from e


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
    """Tool for running tests in isolated Docker sandbox (TRD Table 31)."""

    def __init__(self, runner: Optional[DockerRunner] = None):
        self._runner = runner

    def _get_runner(self) -> DockerRunner:
        if self._runner is None:
            self._runner = get_docker_runner()
        return self._runner

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
        runner = self._get_runner()
        spec = SandboxSpec(
            task_id=ctx.task_id,
            test_command=input_data.test_command,
            timeout_s=30,
            workspace_dir=ctx.workspace_dir,
        )

        try:
            res = runner.run(spec)
            return RunTestsOutput(
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
                passed=(res.exit_code == 0),
            )
        except ServiceUnavailableError as sue:
            raise ToolError(f"503 ServiceUnavailable: {sue}") from sue
        except Exception as e:
            raise ToolError(f"Test execution error: {e}") from e
