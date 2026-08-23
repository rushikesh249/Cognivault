"""Agent Execution API Router (TRD Section 9, Table 12)."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.services.agent_service import (
    AgentService,
    TaskAlreadyRunningError,
    TaskNotFoundError,
    get_agent_service,
)

logger = logging.getLogger("sovereign_workbench.api.agent")

router = APIRouter(prefix="/api/agent", tags=["Agent"])


class AgentRunRequest(BaseModel):
    """Request schema to trigger agent workflow on a task (TRD Table 12)."""
    task_id: str = Field(..., min_length=1, description="Unique task identifier")


class AgentRunOut(BaseModel):
    """Response schema on accepted agent run (TRD Table 12)."""
    task_id: str
    status: str = "running"


@router.post("/run", response_model=AgentRunOut, status_code=status.HTTP_202_ACCEPTED)
async def run_agent_endpoint(
    payload: AgentRunRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentRunOut:
    """
    POST /api/agent/run (TRD Table 12)
    Launches LangGraph agent state machine for the specified task.
    Returns:
    - 202 Accepted: Agent started running.
    - 404 Not Found: Task does not exist.
    - 409 Conflict: Task is already running.
    """
    try:
        service.start_task(payload.task_id)
        return AgentRunOut(task_id=payload.task_id, status="running")
    except TaskNotFoundError as tnfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(tnfe))
    except TaskAlreadyRunningError as tare:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(tare))
    except Exception as e:
        logger.error(f"Unexpected error launching agent task '{payload.task_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to launch agent workflow",
        )
