"""File Upload and Ingestion API Router (TRD Section 9, Table 11)."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from backend.app.services.file_service import FileOut, FileService, get_file_service

logger = logging.getLogger("sovereign_workbench.api.files")

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file_endpoint(
    file: UploadFile = File(..., description="Document (PDF) or Image (JPEG/PNG) file"),
    task_id: Optional[str] = Form(None, description="Associated task identifier"),
    service: FileService = Depends(get_file_service),
) -> FileOut:
    """
    POST /api/files/upload (TRD Table 11)
    Uploads a source PDF/Image file for OCR, RAG ingestion, or vision analysis.
    Returns:
    - 201 Created: File successfully validated and stored.
    - 400 Bad Request: Unsupported mime type or corrupted signature.
    - 413 Payload Too Large: File exceeds 10 MB limit.
    """
    return await service.save_upload(file=file, task_id=task_id)
