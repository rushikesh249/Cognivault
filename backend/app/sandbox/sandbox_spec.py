"""Data models and specifications for code execution sandbox (TRD Section 20, Table 17, Component #16)."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SandboxSpec(BaseModel):
    """Specification for running code/tests within isolated Docker container."""
    task_id: str = Field(..., min_length=1, description="Unique task identifier for workspace isolation")
    code: Optional[str] = Field(default=None, description="Source code text to execute")
    language: str = Field(default="python", description="Programming language (only python supported)")
    test_command: Optional[str] = Field(default=None, description="Test command to run (e.g. pytest)")
    timeout_s: int = Field(default=30, ge=1, le=120, description="Execution timeout in seconds")
    workspace_dir: Optional[Path] = Field(default=None, description="Custom workspace directory path if overridden")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v.lower().strip() != "python":
            raise ValueError(f"Unsupported language '{v}'. Only 'python' is supported in this release.")
        return "python"


class SandboxResult(BaseModel):
    """Structured result returned from Docker sandbox execution."""
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    exit_code: int = Field(default=0, description="Process exit code (e.g. 0 success, 137 OOM)")
    timed_out: bool = Field(default=False, description="True if container was killed due to timeout")
    duration_ms: int = Field(default=0, ge=0, description="Total execution duration in milliseconds")
    passed: Optional[bool] = Field(default=None, description="True if all tests passed (for test runner invocations)")
