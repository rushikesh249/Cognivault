"""File Ingestion and Storage Service (TRD Section 10.3, Table 11, Table 23)."""

import io
import logging
import uuid
from pathlib import Path
from typing import List, Optional
import fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.persistence.db import get_db_context
from backend.app.persistence.file_repository import FileRepository

logger = logging.getLogger("sovereign_workbench.services.file")

MAGIC_SIGNATURES = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}


class FileOut(BaseModel):
    """File metadata response schema (TRD Table 11)."""
    file_id: str
    filename: str
    mime_type: str
    pages: Optional[int] = None
    size_bytes: int


class FileService:
    """Service to handle secure air-gapped file uploads and metadata persistence."""

    def __init__(self, uploads_dir: Optional[Path] = None):
        self.uploads_dir = uploads_dir or settings.paths.uploads_dir
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(
        self,
        file: UploadFile,
        task_id: Optional[str] = None,
    ) -> FileOut:
        """Validate, store, and register uploaded document or image file."""
        filename = Path(file.filename or "upload.bin").name
        content_type = file.content_type or "application/octet-stream"

        # 1. Validate MIME type
        allowed = settings.upload.allowed_mime_types
        if content_type not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{content_type}'. Allowed types: {allowed}",
            )

        # 2. Read content and enforce size limits
        content = await file.read()
        size_bytes = len(content)
        max_bytes = settings.upload.max_upload_bytes

        if size_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({size_bytes} bytes) exceeds maximum allowable limit ({max_bytes} bytes).",
            )

        # 3. Magic number signature verification
        expected_sig = MAGIC_SIGNATURES.get(content_type)
        if expected_sig and not content.startswith(expected_sig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File signature mismatch for declared MIME type '{content_type}'.",
            )

        # 4. Save to data/uploads with UUID prefix to prevent traversal/collision
        file_id = str(uuid.uuid4())
        suffix = Path(filename).suffix.lower() or ".bin"
        storage_filename = f"{file_id}{suffix}"
        target_path = (self.uploads_dir / storage_filename).resolve()

        # Enforce canonical path containment
        canon_uploads = self.uploads_dir.resolve()
        if not target_path.is_relative_to(canon_uploads):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security: Invalid upload destination path.",
            )

        with open(target_path, "wb") as f:
            f.write(content)

        # 5. Extract page count if PDF
        pages: Optional[int] = None
        if content_type == "application/pdf":
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                pages = len(doc)
                doc.close()
            except Exception as e:
                logger.warning(f"Failed to inspect PDF pages: {e}")
                pages = 1

        # 6. Register in SQLite files table
        with get_db_context() as session:
            repo = FileRepository(session)
            repo.create(
                file_id=file_id,
                task_id=task_id,
                filename=filename,
                mime_type=content_type,
                pages=pages,
                size_bytes=size_bytes,
                storage_path=str(target_path),
            )

        logger.info(f"Saved uploaded file: {target_path} (id: {file_id}, size: {size_bytes})")
        return FileOut(
            file_id=file_id,
            filename=filename,
            mime_type=content_type,
            pages=pages,
            size_bytes=size_bytes,
        )


_file_service_instance: Optional[FileService] = None


def get_file_service() -> FileService:
    global _file_service_instance
    if _file_service_instance is None:
        _file_service_instance = FileService()
    return _file_service_instance
