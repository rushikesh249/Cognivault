"""File Tools with strict workspace boundary enforcement (TRD Section 12, Table 31, Component #15)."""

import logging
import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.tools.base import (
    BaseTool,
    PathEscapeError,
    ToolContext,
    ToolError,
    ToolMetadata,
)

logger = logging.getLogger("sovereign_workbench.tools.file")
security_logger = logging.getLogger("sovereign_workbench.security")


# ==============================================================================
# Workspace Path Containment Helper
# ==============================================================================

def get_workspace_dir(ctx: ToolContext) -> Path:
    """Get or create the isolated workspace directory for the task."""
    if ctx.workspace_dir is not None:
        ws = ctx.workspace_dir
    else:
        ws = Path(settings.paths.data_dir) / "sandbox" / ctx.task_id
    ws.mkdir(parents=True, exist_ok=True)
    return ws.resolve()


def resolve_contained_path(rel_path: str, ctx: ToolContext) -> Path:
    """Resolve and validate that a requested path strictly resides within the task workspace sandbox.
    
    Raises PathEscapeError and logs a structured security event if a traversal attempt is detected.
    """
    workspace_root = get_workspace_dir(ctx)
    
    if not rel_path or not rel_path.strip():
        return workspace_root

    clean_rel = rel_path.strip()
    
    # Check for direct suspicious tokens before resolution
    target = (workspace_root / clean_rel).resolve()

    # Verify that target is strictly within workspace_root
    try:
        target.relative_to(workspace_root)
    except ValueError:
        # Path escape detected!
        security_logger.warning(
            "Path escape violation detected",
            extra={
                "event_type": "path_escape_attempt",
                "task_id": ctx.task_id,
                "task_type": ctx.task_type,
                "requested_path": clean_rel,
                "workspace_root": str(workspace_root),
                "resolved_target": str(target),
            },
        )
        raise PathEscapeError(
            f"Security violation: Requested path '{clean_rel}' resolves outside the task workspace sandbox '{workspace_root}'."
        )

    # Check symlink destination if target exists and is a symlink
    if os.path.islink(target):
        real_target = Path(os.path.realpath(target))
        try:
            real_target.relative_to(workspace_root)
        except ValueError:
            security_logger.warning(
                "Symlink escape violation detected",
                extra={
                    "event_type": "symlink_escape_attempt",
                    "task_id": ctx.task_id,
                    "task_type": ctx.task_type,
                    "requested_path": clean_rel,
                    "workspace_root": str(workspace_root),
                    "symlink_target": str(real_target),
                },
            )
            raise PathEscapeError(
                f"Security violation: Symlink '{clean_rel}' targets a path outside the task workspace sandbox."
            )

    return target


# ==============================================================================
# 1. read_file
# ==============================================================================

class ReadFileInput(BaseModel):
    path: str = Field(..., min_length=1, description="Relative path of file within workspace")


class ReadFileOutput(BaseModel):
    content: str = Field(..., description="UTF-8 decoded file content")


class ReadFileTool(BaseTool):
    """Tool to read a file within the task workspace (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            purpose="Read a file within the task workspace.",
            input_schema=ReadFileInput,
            output_schema=ReadFileOutput,
            allowed_task_types=["document", "coding"],
            timeout_s=5.0,
            fs_boundary="workspace dir only",
            network="none",
        )

    def execute(self, input_data: ReadFileInput, ctx: ToolContext) -> ReadFileOutput:
        target_path = resolve_contained_path(input_data.path, ctx)
        if not target_path.exists() or not target_path.is_file():
            raise ToolError(f"FileNotFoundError: File '{input_data.path}' does not exist in workspace.")

        try:
            content = target_path.read_text(encoding="utf-8")
            return ReadFileOutput(content=content)
        except Exception as e:
            raise ToolError(f"Failed to read file '{input_data.path}': {e}") from e


# ==============================================================================
# 2. write_file
# ==============================================================================

class WriteFileInput(BaseModel):
    path: str = Field(..., min_length=1, description="Relative path of file within workspace")
    content: str = Field(..., description="Text content to write")


class WriteFileOutput(BaseModel):
    bytes_written: int = Field(..., ge=0, description="Total bytes written to disk")


class WriteFileTool(BaseTool):
    """Tool to write a file within the task workspace (TRD Table 31). Allowed for coding only."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            purpose="Write a file within the task workspace.",
            input_schema=WriteFileInput,
            output_schema=WriteFileOutput,
            allowed_task_types=["coding"],
            timeout_s=5.0,
            fs_boundary="workspace dir only",
            network="none",
        )

    def execute(self, input_data: WriteFileInput, ctx: ToolContext) -> WriteFileOutput:
        target_path = resolve_contained_path(input_data.path, ctx)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            encoded = input_data.content.encode("utf-8")
            target_path.write_bytes(encoded)
            return WriteFileOutput(bytes_written=len(encoded))
        except Exception as e:
            raise ToolError(f"Failed to write file '{input_data.path}': {e}") from e


# ==============================================================================
# 3. list_files
# ==============================================================================

class ListFilesInput(BaseModel):
    path: str = Field(default=".", description="Relative directory path within workspace")


class ListFilesOutput(BaseModel):
    entries: List[str] = Field(default_factory=list, description="List of file/directory names in directory")


class ListFilesTool(BaseTool):
    """Tool to list entries in a workspace directory (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="list_files",
            purpose="List files in a workspace directory.",
            input_schema=ListFilesInput,
            output_schema=ListFilesOutput,
            allowed_task_types=["document", "coding"],
            timeout_s=5.0,
            fs_boundary="workspace dir only",
            network="none",
        )

    def execute(self, input_data: ListFilesInput, ctx: ToolContext) -> ListFilesOutput:
        target_path = resolve_contained_path(input_data.path, ctx)
        
        # Missing directory returns empty list without error (TRD Table 31 specification)
        if not target_path.exists() or not target_path.is_dir():
            return ListFilesOutput(entries=[])

        try:
            entries = sorted([p.name for p in target_path.iterdir()])
            return ListFilesOutput(entries=entries)
        except Exception as e:
            raise ToolError(f"Failed to list directory '{input_data.path}': {e}") from e
