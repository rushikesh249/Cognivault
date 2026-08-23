"""Direct Code Execution REST API Router (TRD Section 9, Table 17)."""

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.app.sandbox.docker_runner import DockerRunner, ServiceUnavailableError, get_docker_runner
from backend.app.sandbox.sandbox_spec import SandboxSpec

logger = logging.getLogger("sovereign_workbench.api.code")

router = APIRouter(prefix="/api/code", tags=["code"])


class CodeExecRequest(BaseModel):
    """Request schema for code execution (TRD Table 17)."""
    language: str = Field(default="python", description="Programming language (only python supported)")
    code: str = Field(..., min_length=1, description="Source code text to execute")
    test_command: Optional[str] = Field(default=None, description="Optional test runner command")
    timeout_s: int = Field(default=30, ge=1, le=120, description="Execution timeout in seconds")

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v.lower().strip() != "python":
            raise ValueError(f"Unsupported language '{v}'. Only 'python' is supported.")
        return "python"

    @field_validator("code")
    @classmethod
    def validate_code_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Code parameter must not be empty or whitespace only")
        return v


class CodeExecResult(BaseModel):
    """Response schema for code execution (TRD Table 17)."""
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    duration_ms: int


@router.post("/execute", response_model=CodeExecResult, status_code=status.HTTP_200_OK)
async def execute_code_endpoint(
    payload: CodeExecRequest,
    runner: DockerRunner = Depends(get_docker_runner),
) -> CodeExecResult:
    """Execute code in isolated Docker sandbox container (TRD Table 17)."""
    task_id = f"api_exec_{uuid.uuid4().hex[:8]}"
    spec = SandboxSpec(
        task_id=task_id,
        code=payload.code,
        language=payload.language,
        test_command=payload.test_command,
        timeout_s=payload.timeout_s,
    )

    try:
        res = runner.run(spec)
        return CodeExecResult(
            stdout=res.stdout,
            stderr=res.stderr,
            exit_code=res.exit_code,
            timed_out=res.timed_out,
            duration_ms=res.duration_ms,
        )
    except ServiceUnavailableError as sue:
        logger.error(f"Docker unavailable during code execution: {sue}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker daemon is unavailable. Host execution fallback is strictly prohibited.",
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in code execution endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Code execution failed")
