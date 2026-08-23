"""Unit tests for Sandbox Specification and Schemas (TRD Section 20, Table 17)."""

import pytest
from pydantic import ValidationError

from backend.app.api.code import CodeExecRequest
from backend.app.sandbox.sandbox_spec import SandboxSpec, SandboxResult


def test_sandbox_spec_valid():
    """Verify valid SandboxSpec creation."""
    spec = SandboxSpec(task_id="task_123", code="print('hello')", timeout_s=15)
    assert spec.task_id == "task_123"
    assert spec.language == "python"
    assert spec.code == "print('hello')"
    assert spec.timeout_s == 15


def test_sandbox_spec_unsupported_language_rejected():
    """Verify unsupported languages are rejected with validation error."""
    with pytest.raises(ValidationError):
        SandboxSpec(task_id="task_123", code="echo 'hello'", language="bash")

    with pytest.raises(ValidationError):
        SandboxSpec(task_id="task_123", code="int main(){}", language="c++")


def test_sandbox_spec_timeout_bounds():
    """Verify timeout_s must be within allowed bounds (1 to 120s)."""
    with pytest.raises(ValidationError):
        SandboxSpec(task_id="task_123", code="print('test')", timeout_s=0)

    with pytest.raises(ValidationError):
        SandboxSpec(task_id="task_123", code="print('test')", timeout_s=200)


def test_code_exec_request_validation():
    """Verify CodeExecRequest validation rules."""
    req = CodeExecRequest(code="x = 10\nprint(x)")
    assert req.language == "python"
    assert req.timeout_s == 30

    # Empty code is rejected
    with pytest.raises(ValidationError):
        CodeExecRequest(code="")

    # Whitespace only is rejected
    with pytest.raises(ValidationError):
        CodeExecRequest(code="   ")

    # Unsupported language is rejected
    with pytest.raises(ValidationError):
        CodeExecRequest(code="print(1)", language="ruby")
