"""Integration tests for Tool Registry, File Sandbox containment, and RAG Tool (TRD Section 12, Component #14, #15)."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from backend.app.services.rag_service import RAGService
from backend.app.tools.base import (
    PathEscapeError,
    ToolContext,
    ToolError,
    ToolPermissionError,
)
from backend.app.tools.kb_tools import SearchKnowledgeBaseTool
from backend.app.tools.tool_registry import ToolRegistry


class MockRAGService(RAGService):
    """Mock RAG service for deterministic tool integration testing."""

    def __init__(self, sample_matches: Optional[List[Dict[str, Any]]] = None):
        self._sample_matches = sample_matches or [
            {
                "text": "In the event of uncontrolled hydrocarbon release, the Emergency Shutdown System (ESD) must be initiated.",
                "source_document": "safety_sop.md",
                "section": "1.1 Process Unit Emergency Shutdown",
                "score": 0.89,
                "page": 1,
                "citation": "safety_sop.md - 1.1 Process Unit Emergency Shutdown (p.1)",
            }
        ]

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            raise ValueError("Query string must not be empty or whitespace only")
        return self._sample_matches[: (top_k or 5)]


@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "sandbox_task_123"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def registry_with_rag():
    """Initialize ToolRegistry with a mock test RAG service."""
    mock_rag = MockRAGService()
    reg = ToolRegistry()
    reg.register_tool(SearchKnowledgeBaseTool(rag_service=mock_rag))
    return reg


def test_file_tools_workspace_lifecycle(temp_workspace):
    """Test full file write, read, list lifecycle within isolated workspace."""
    reg = ToolRegistry()
    ctx = ToolContext(task_id="task-lifecycle", task_type="coding", workspace_dir=temp_workspace)

    # 1. Write file
    write_res = reg.invoke("write_file", {"path": "src/main.py", "content": "print('Hello Sovereign')"}, ctx)
    assert write_res.success is True
    assert write_res.data["bytes_written"] > 0

    # 2. Read file
    read_res = reg.invoke("read_file", {"path": "src/main.py"}, ctx)
    assert read_res.success is True
    assert read_res.data["content"] == "print('Hello Sovereign')"

    # 3. List files in src
    list_res = reg.invoke("list_files", {"path": "src"}, ctx)
    assert list_res.success is True
    assert "main.py" in list_res.data["entries"]

    # 4. List non-existent directory returns [] without error (TRD Table 31)
    empty_list_res = reg.invoke("list_files", {"path": "non_existent_folder"}, ctx)
    assert empty_list_res.success is True
    assert empty_list_res.data["entries"] == []

    # 5. Read non-existent file raises structured ToolError
    with pytest.raises(ToolError) as exc_info:
        reg.invoke("read_file", {"path": "non_existent.txt"}, ctx)
    assert "FileNotFoundError" in str(exc_info.value)


def test_path_escape_traversal_rejection(temp_workspace):
    """Verify ../ path traversal outside workspace is rejected with PathEscapeError."""
    reg = ToolRegistry()
    ctx = ToolContext(task_id="task-escape-1", task_type="coding", workspace_dir=temp_workspace)

    # Attempt to read outside workspace
    with pytest.raises(PathEscapeError):
        reg.invoke("read_file", {"path": "../../../configs/app.yaml"}, ctx)

    # Attempt to write outside workspace
    with pytest.raises(PathEscapeError):
        reg.invoke("write_file", {"path": "../escape.txt", "content": "evil"}, ctx)

    # Attempt to list outside workspace
    with pytest.raises(PathEscapeError):
        reg.invoke("list_files", {"path": "../../"}, ctx)


def test_path_escape_absolute_path_rejection(temp_workspace):
    """Verify absolute paths outside the workspace are rejected."""
    reg = ToolRegistry()
    ctx = ToolContext(task_id="task-escape-2", task_type="coding", workspace_dir=temp_workspace)

    # Absolute path to Windows system / root
    with pytest.raises(PathEscapeError):
        reg.invoke("read_file", {"path": "C:/Windows/System32/drivers/etc/hosts"}, ctx)


def test_symlink_escape_rejection(temp_workspace, tmp_path):
    """Verify symlinks pointing outside workspace root are rejected."""
    reg = ToolRegistry()
    ctx = ToolContext(task_id="task-symlink", task_type="coding", workspace_dir=temp_workspace)

    external_file = tmp_path / "secret_outside.txt"
    external_file.write_text("classified data", encoding="utf-8")

    symlink_path = temp_workspace / "symlink_escape"
    try:
        os.symlink(str(external_file), str(symlink_path))
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation requires elevated permissions on this environment")

    with pytest.raises(PathEscapeError):
        reg.invoke("read_file", {"path": "symlink_escape"}, ctx)


def test_real_rag_search_through_tool_registry(registry_with_rag):
    """Verify search_knowledge_base tool performs RAG search and returns ranked citations."""
    ctx = ToolContext(task_id="rag-tool-task", task_type="document")

    res = registry_with_rag.invoke(
        "search_knowledge_base",
        {"query": "Emergency shutdown ESD procedures", "top_k": 3},
        ctx,
    )

    assert res.success is True
    assert "matches" in res.data
    matches = res.data["matches"]
    assert len(matches) > 0
    assert matches[0]["source_document"] == "safety_sop.md"
    assert matches[0]["score"] >= 0.55
    assert "safety_sop.md" in matches[0]["citation"]
