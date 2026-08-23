"""Repository for Tasks and TaskEvents (TRD Component #19)."""

import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.persistence.models import TaskORM, TaskEventORM, generate_uuid, get_utc_now


class TaskRepository:
    """Thread-safe database operations for tasks and task events."""

    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        title: str,
        task_type: str,
        prompt: str,
        task_id: Optional[str] = None,
    ) -> TaskORM:
        now = get_utc_now()
        task = TaskORM(
            task_id=task_id or generate_uuid(),
            title=title,
            task_type=task_type,
            prompt=prompt,
            status="created",
            created_at=now,
            updated_at=now,
        )
        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        return task

    def get_by_id(self, task_id: str) -> Optional[TaskORM]:
        return self._session.query(TaskORM).filter(TaskORM.task_id == task_id).first()

    def list_tasks(self, limit: int = 50, offset: int = 0) -> List[TaskORM]:
        return (
            self._session.query(TaskORM)
            .order_by(TaskORM.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        task_id: str,
        status: str,
        model_used: Optional[str] = None,
    ) -> Optional[TaskORM]:
        task = self.get_by_id(task_id)
        if not task:
            return None
        task.status = status
        if model_used is not None:
            task.model_used = model_used
        task.updated_at = get_utc_now()
        self._session.commit()
        self._session.refresh(task)
        return task

    def add_event(
        self,
        task_id: str,
        node: str,
        message: str,
        level: str = "info",
    ) -> TaskEventORM:
        event = TaskEventORM(
            event_id=generate_uuid(),
            task_id=task_id,
            node=node,
            message=message,
            level=level,
            ts=get_utc_now(),
        )
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

    def get_events(self, task_id: str) -> List[TaskEventORM]:
        return (
            self._session.query(TaskEventORM)
            .filter(TaskEventORM.task_id == task_id)
            .order_by(TaskEventORM.ts.asc())
            .all()
        )
