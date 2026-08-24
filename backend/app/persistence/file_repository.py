"""Repository for Uploaded Files (TRD Section 10.3, Table 23)."""

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.persistence.models import FileORM, generate_uuid, get_utc_now


class FileRepository:
    """Thread-safe database operations for uploaded source files."""

    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        filename: str,
        mime_type: str,
        size_bytes: int,
        storage_path: str,
        pages: Optional[int] = None,
        task_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ) -> FileORM:
        file_obj = FileORM(
            file_id=file_id or generate_uuid(),
            task_id=task_id,
            filename=filename,
            mime_type=mime_type,
            pages=pages,
            size_bytes=size_bytes,
            storage_path=storage_path,
            uploaded_at=get_utc_now(),
        )
        self._session.add(file_obj)
        self._session.commit()
        self._session.refresh(file_obj)
        return file_obj

    def get_by_id(self, file_id: str) -> Optional[FileORM]:
        return self._session.query(FileORM).filter(FileORM.file_id == file_id).first()

    def list_by_task_id(self, task_id: str) -> List[FileORM]:
        return (
            self._session.query(FileORM)
            .filter(FileORM.task_id == task_id)
            .order_by(FileORM.uploaded_at.asc())
            .all()
        )

    def list_files(self, limit: int = 50, offset: int = 0) -> List[FileORM]:
        return (
            self._session.query(FileORM)
            .order_by(FileORM.uploaded_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
