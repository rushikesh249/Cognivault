"""Artifact Retrieval and Download API Router (TRD Section 9, Table 18)."""

import logging
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse

from backend.app.services.artifact_service import (
    ArtifactMeta,
    ArtifactService,
    get_artifact_service,
)

logger = logging.getLogger("sovereign_workbench.api.artifacts")

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


@router.get("", response_model=List[ArtifactMeta])
async def list_artifacts_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ArtifactService = Depends(get_artifact_service),
) -> List[ArtifactMeta]:
    """List all registered artifacts with source citations."""
    return service.list_all(limit=limit, offset=offset)


@router.get("/{artifact_id}")
async def get_artifact_endpoint(
    artifact_id: str,
    meta: bool = Query(False, description="Set to true to fetch metadata instead of downloading binary file"),
    service: ArtifactService = Depends(get_artifact_service),
):
    """
    GET /api/artifacts/{artifact_id} (TRD Table 18)
    Retrieves either:
    - Binary download of the artifact file (default, meta=false).
    - JSON metadata with RAG sources list (meta=true).
    Returns:
    - 200 OK: Binary stream or JSON metadata.
    - 404 Not Found: Artifact record not found in database.
    - 410 Gone: Artifact record exists but file is missing on disk.
    """
    if meta:
        return service.get_meta(artifact_id)

    file_path = service.get_file_path(artifact_id)
    filename = file_path.name

    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif filename.endswith(".pptx"):
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )
