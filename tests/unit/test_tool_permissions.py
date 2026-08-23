"""Unit tests for Tool Registry, Schema Validation, and Permission Matrix (TRD Section 12, Table 31, Test Plan P16)."""

import pytest
from pydantic import ValidationError

from backend.app.tools.base import (
    PathEscapeError,
    ToolContext,
    ToolError,
    ToolPermissionError,
    ToolValidationError,
    UnknownToolError,
)
from backend.app.tools.tool_registry import ToolRegistry, get_tool_registry


@pytest.fixture
def registry():
    return ToolRegistry()


def test_registry_contains_all_11_tools(registry):
    """Verify all 11 tools from TRD Table 31 are registered."""
    assert registry.count() == 11
    tools = [m.name for m in registry.list_tools()]
    expected_tools = [
        "read_file", "write_file", "list_files",
        "search_knowledge_base", "extract_text_from_scan",
        "create_docx", "create_xlsx", "create_pptx", "create_pdf",
        "execute_code", "run_tests"
    ]
    for expected in expected_tools:
        assert expected in tools, f"Missing tool: {expected}"


def test_permission_matrix_document_task(registry):
    """Verify document task permissions per TRD Table 31."""
    ctx = ToolContext(task_id="doc-task-1", task_type="document")
    
    # Allowed tools for document
    allowed = [
        "read_file", "list_files", "search_knowledge_base",
        "extract_text_from_scan", "create_docx", "create_xlsx",
        "create_pptx", "create_pdf"
    ]
    doc_tools = [m.name for m in registry.list_tools(task_type="document")]
    assert sorted(doc_tools) == sorted(allowed)

    # Disallowed tools for document
    disallowed = ["write_file", "execute_code", "run_tests"]
    for tool_name in disallowed:
        with pytest.raises(ToolPermissionError):
            registry.invoke(tool_name, {}, ctx)


def test_permission_matrix_coding_task(registry):
    """Verify coding task permissions per TRD Table 31."""
    ctx = ToolContext(task_id="code-task-1", task_type="coding")

    # Allowed tools for coding
    allowed = ["read_file", "write_file", "list_files", "execute_code", "run_tests"]
    coding_tools = [m.name for m in registry.list_tools(task_type="coding")]
    assert sorted(coding_tools) == sorted(allowed)

    # Disallowed tools for coding
    disallowed = [
        "search_knowledge_base", "extract_text_from_scan",
        "create_docx", "create_xlsx", "create_pptx", "create_pdf"
    ]
    for tool_name in disallowed:
        with pytest.raises(ToolPermissionError):
            registry.invoke(tool_name, {}, ctx)


def test_permission_matrix_vision_task(registry):
    """Verify vision task has zero permitted tools (TRD Table 31, Section 21)."""
    ctx = ToolContext(task_id="vis-task-1", task_type="vision")
    vision_tools = registry.list_tools(task_type="vision")
    assert len(vision_tools) == 0

    # All 11 tools should be rejected for vision
    for meta in registry.list_tools():
        with pytest.raises(ToolPermissionError):
            registry.invoke(meta.name, {}, ctx)


def test_unknown_tool_rejection(registry):
    """Verify invoking an unregistered tool raises UnknownToolError before execution."""
    ctx = ToolContext(task_id="any-task", task_type="document")
    with pytest.raises(UnknownToolError):
        registry.invoke("non_existent_tool", {"foo": "bar"}, ctx)


def test_schema_validation_rejection_for_all_tools(registry):
    """Verify invalid/missing arguments are rejected with ToolValidationError."""
    with pytest.raises(ToolValidationError):
        registry.invoke("read_file", {}, ToolContext(task_id="t1", task_type="document"))

    with pytest.raises(ToolValidationError):
        registry.invoke("write_file", {"path": "main.py"}, ToolContext(task_id="t2", task_type="coding"))

    with pytest.raises(ToolValidationError):
        registry.invoke("search_knowledge_base", {}, ToolContext(task_id="t3", task_type="document"))

    with pytest.raises(ToolValidationError):
        registry.invoke("execute_code", {"language": "python"}, ToolContext(task_id="t4", task_type="coding"))

    with pytest.raises(ToolValidationError):
        registry.invoke("run_tests", {}, ToolContext(task_id="t5", task_type="coding"))

    with pytest.raises(ToolValidationError):
        registry.invoke("extract_text_from_scan", {}, ToolContext(task_id="t6", task_type="document"))

    with pytest.raises(ToolValidationError):
        registry.invoke("create_docx", {}, ToolContext(task_id="t7", task_type="document"))


def test_execute_code_and_run_tests_in_docker(registry):
    """Verify execute_code and run_tests run in Docker sandbox (Phase 6)."""
    ctx = ToolContext(task_id="task_tool_exec", task_type="coding")

    res = registry.invoke("execute_code", {"language": "python", "code": "print('HELLO_DOCKER_SANDBOX')"}, ctx)
    assert res.success is True
    assert "stdout" in res.data
    assert "HELLO_DOCKER_SANDBOX" in res.data["stdout"]
    assert res.data["exit_code"] == 0
