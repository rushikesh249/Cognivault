"""Task Manager application service (TRD Component #3, §8.1)."""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.persistence.task_repository import TaskRepository

logger = logging.getLogger("sovereign_workbench.services.tasks")

VALID_TASK_TYPES = {"document", "coding", "vision"}
VALID_STATUSES = {"created", "running", "succeeded", "failed", "failed_bounded"}


class TaskServiceError(Exception):
    """Base exception for task service errors."""
    pass


class TaskNotFoundError(TaskServiceError):
    """Raised when a requested task does not exist."""
    pass


class InvalidTaskPayloadError(TaskServiceError):
    """Raised when task creation input violates constraints."""
    pass


class TaskService:
    """
    Application service managing task lifecycles (TRD Component #3).
    Note: Follows TRD §8.1 layering rule — does not import FastAPI types.
    """

    def __init__(self, session: Session):
        self._repo = TaskRepository(session)

    def create_task(
        self,
        title: str,
        task_type: str,
        prompt: str,
        file_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate and persist a new task (POST /api/tasks)."""
        if not title or not title.strip():
            raise InvalidTaskPayloadError("Task title must not be empty.")
        if task_type not in VALID_TASK_TYPES:
            raise InvalidTaskPayloadError(
                f"Invalid task_type '{task_type}'. Allowed types: {sorted(list(VALID_TASK_TYPES))}"
            )
        if not prompt or not prompt.strip():
            raise InvalidTaskPayloadError("Task prompt must not be empty.")

        task = self._repo.create(
            title=title.strip(),
            task_type=task_type,
            prompt=prompt.strip(),
        )
        logger.info(f"Created task {task.task_id} (type={task.task_type}, title='{task.title}')")
        return {
            "task_id": task.task_id,
            "title": task.title,
            "task_type": task.task_type,
            "prompt": task.prompt,
            "status": task.status,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "file_ids": file_ids or [],
        }

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Retrieve task details by task_id (GET /api/tasks/{task_id})."""
        task = self._repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID '{task_id}' not found.")

        return {
            "task_id": task.task_id,
            "title": task.title,
            "task_type": task.task_type,
            "prompt": task.prompt,
            "status": task.status,
            "model_used": task.model_used,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "artifact_ids": [],  # Populated in later artifact phases
        }

    def update_task_status(
        self,
        task_id: str,
        status: str,
        model_used: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update task execution state."""
        if status not in VALID_STATUSES:
            raise InvalidTaskPayloadError(f"Invalid status '{status}'. Allowed: {VALID_STATUSES}")
        task = self._repo.update_status(task_id, status, model_used=model_used)
        if not task:
            raise TaskNotFoundError(f"Task with ID '{task_id}' not found.")
        return {
            "task_id": task.task_id,
            "status": task.status,
            "model_used": task.model_used,
            "updated_at": task.updated_at,
        }
