"""Artifact Management Service (TRD Section 10.5, Table 18, Table 25)."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel

from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context

logger = logging.getLogger("sovereign_workbench.services.artifact")


class ArtifactMeta(BaseModel):
    """Artifact metadata response schema (TRD Table 18)."""
    artifact_id: str
    task_id: str
    kind: str
    title: str
    sources: List[str]
    created_at: str


class ArtifactService:
    """Service to query, retrieve, and download generated deliverables."""

    def __init__(self):
        pass

    def get_meta(self, artifact_id: str) -> ArtifactMeta:
        """Fetch metadata for a registered artifact."""
        with get_db_context() as session:
            repo = ArtifactRepository(session)
            art = repo.get_by_id(artifact_id)
            if not art:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{artifact_id}' not found.",
                )

            try:
                sources = json.loads(art.sources_json)
            except Exception:
                sources = []

            return ArtifactMeta(
                artifact_id=art.artifact_id,
                task_id=art.task_id,
                kind=art.kind,
                title=art.title,
                sources=sources,
                created_at=art.created_at.isoformat(),
            )

    def get_file_path(self, artifact_id: str) -> Path:
        """Retrieve verified on-disk filesystem path for an artifact file."""
        with get_db_context() as session:
            repo = ArtifactRepository(session)
            art = repo.get_by_id(artifact_id)
            if not art:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{artifact_id}' not found in database.",
                )

            storage_path = Path(art.storage_path)
            if not storage_path.exists():
                # TRD Table 18: 410 file missing on disk
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail=f"Artifact file for '{artifact_id}' was removed or is missing from disk.",
                )

            return storage_path

    def list_all(self, limit: int = 50, offset: int = 0) -> List[ArtifactMeta]:
        """List all generated artifacts."""
        with get_db_context() as session:
            repo = ArtifactRepository(session)
            items = repo.list_artifacts(limit=limit, offset=offset)
            results = []
            for art in items:
                try:
                    sources = json.loads(art.sources_json)
                except Exception:
                    sources = []
                results.append(
                    ArtifactMeta(
                        artifact_id=art.artifact_id,
                        task_id=art.task_id,
                        kind=art.kind,
                        title=art.title,
                        sources=sources,
                        created_at=art.created_at.isoformat(),
                    )
                )
            return results


_artifact_service_instance: Optional[ArtifactService] = None


def get_artifact_service() -> ArtifactService:
    global _artifact_service_instance
    if _artifact_service_instance is None:
        _artifact_service_instance = ArtifactService()
    return _artifact_service_instance
