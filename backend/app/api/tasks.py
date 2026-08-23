"""Task Manager API router (TRD §9, Table 9 & Table 13)."""

import datetime
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.persistence.db import get_db
from backend.app.services.task_service import (
    InvalidTaskPayloadError,
    TaskNotFoundError,
    TaskService,
)

router = APIRouter(prefix="/api", tags=["Tasks"])


class TaskCreate(BaseModel):
    """Request schema for POST /api/tasks (TRD Table 9)."""
    title: str = Field(..., min_length=1, description="Task title")
    task_type: Literal["document", "coding", "vision"] = Field(..., description="Task category")
    prompt: str = Field(..., min_length=1, description="Task instructions/prompt")
    file_ids: List[str] = Field(default_factory=list, description="Attached file IDs")


class TaskOut(BaseModel):
    """Response schema for POST /api/tasks (TRD Table 9)."""
    task_id: str
    status: str = "created"
    created_at: datetime.datetime


class TaskDetail(BaseModel):
    """Response schema for GET /api/tasks/{task_id} (TRD Table 13)."""
    task_id: str
    title: str
    task_type: str
    prompt: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    artifact_ids: List[str] = Field(default_factory=list)
    model_used: Optional[str] = None


def get_task_service(session: Session = Depends(get_db)) -> TaskService:
    return TaskService(session)


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskOut:
    """
    Create a new task (TRD §9). Does not start agent execution.
    """
    try:
        result = service.create_task(
            title=payload.title,
            task_type=payload.task_type,
            prompt=payload.prompt,
            file_ids=payload.file_ids,
        )
        return TaskOut(
            task_id=result["task_id"],
            status=result["status"],
            created_at=result["created_at"],
        )
    except InvalidTaskPayloadError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskDetail, status_code=status.HTTP_200_OK)
async def get_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskDetail:
    """
    Fetch task details and status by task_id (TRD §9, Table 13).
    """
    try:
        task = service.get_task(task_id)
        return TaskDetail(
            task_id=task["task_id"],
            title=task["title"],
            task_type=task["task_type"],
            prompt=task["prompt"],
            status=task["status"],
            created_at=task["created_at"],
            updated_at=task["updated_at"],
            artifact_ids=task["artifact_ids"],
            model_used=task["model_used"],
        )
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
