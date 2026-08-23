"""Repository for Generated Artifacts (TRD Section 10.5, Table 25)."""

import json
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.persistence.models import ArtifactORM, generate_uuid, get_utc_now


class ArtifactRepository:
    """Thread-safe database operations for generated artifacts."""

    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        task_id: str,
        kind: str,
        title: str,
        storage_path: str,
        sources: Optional[List[str]] = None,
        artifact_id: Optional[str] = None,
    ) -> ArtifactORM:
        sources_json = json.dumps(sources or [])
        artifact = ArtifactORM(
            artifact_id=artifact_id or generate_uuid(),
            task_id=task_id,
            kind=kind,
            title=title,
            storage_path=storage_path,
            sources_json=sources_json,
            created_at=get_utc_now(),
        )
        self._session.add(artifact)
        self._session.commit()
        self._session.refresh(artifact)
        return artifact

    def get_by_id(self, artifact_id: str) -> Optional[ArtifactORM]:
        return self._session.query(ArtifactORM).filter(ArtifactORM.artifact_id == artifact_id).first()

    def list_by_task_id(self, task_id: str) -> List[ArtifactORM]:
        return (
            self._session.query(ArtifactORM)
            .filter(ArtifactORM.task_id == task_id)
            .order_by(ArtifactORM.created_at.asc())
            .all()
        )

    def list_artifacts(self, limit: int = 50, offset: int = 0) -> List[ArtifactORM]:
        return (
            self._session.query(ArtifactORM)
            .order_by(ArtifactORM.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
