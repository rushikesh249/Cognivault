"""Task Events SSE Streaming API Router (TRD Section 9, Table 14)."""

import asyncio
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.app.agent.event_broadcaster import get_event_broadcaster
from backend.app.persistence.db import get_db_context
from backend.app.persistence.task_repository import TaskRepository

logger = logging.getLogger("sovereign_workbench.api.events")

router = APIRouter(prefix="/api/tasks", tags=["Events"])


async def event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """Yield historical and live Server-Sent Events for a task."""
    broadcaster = get_event_broadcaster()
    queue = await broadcaster.subscribe(task_id)
    seen_event_ids = set()

    try:
        # 1. Historical Replay: Query durable events from SQLite inside session
        past_event_dicts = []
        is_terminal = False
        with get_db_context() as session:
            repo = TaskRepository(session)
            task = repo.get_by_id(task_id)
            if not task:
                return
            for ev in repo.get_events(task_id):
                past_event_dicts.append({
                    "event_id": ev.event_id,
                    "task_id": ev.task_id,
                    "node": ev.node,
                    "message": ev.message,
                    "level": ev.level,
                    "ts": ev.ts.isoformat(),
                })
            is_terminal = task.status in ["succeeded", "failed", "failed_bounded"]

        for ev_dict in past_event_dicts:
            seen_event_ids.add(ev_dict["event_id"])
            yield f"data: {json.dumps(ev_dict)}\n\n"

        # If task was already terminal, stop here
        if is_terminal:
            return

        # 2. Live Stream: Read from in-memory subscriber queue
        while True:
            try:
                # Wait for next live event with timeout to check task status periodically
                event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                if event_data["event_id"] not in seen_event_ids:
                    seen_event_ids.add(event_data["event_id"])
                    yield f"data: {json.dumps(event_data)}\n\n"

                    # If this is the terminal final_deliverable event, close stream
                    if event_data.get("node") == "final_deliverable":
                        break
            except asyncio.TimeoutError:
                # Periodic check if task has terminated in database
                with get_db_context() as session:
                    repo = TaskRepository(session)
                    task = repo.get_by_id(task_id)
                    if task and task.status in ["succeeded", "failed", "failed_bounded"]:
                        # Drain any remaining events in queue
                        while not queue.empty():
                            ev = queue.get_nowait()
                            if ev["event_id"] not in seen_event_ids:
                                seen_event_ids.add(ev["event_id"])
                                yield f"data: {json.dumps(ev)}\n\n"
                        break

    except asyncio.CancelledError:
        logger.info(f"Client disconnected from SSE stream for task '{task_id}'")
    finally:
        await broadcaster.unsubscribe(task_id, queue)


@router.get("/{task_id}/events")
async def stream_task_events(task_id: str) -> StreamingResponse:
    """
    GET /api/tasks/{task_id}/events (TRD Section 9, Table 14)
    Server-Sent Events (SSE) stream of TaskEvent objects.
    Replays full durable event history from SQLite and streams live node transitions.
    """
    with get_db_context() as session:
        repo = TaskRepository(session)
        task = repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    return StreamingResponse(
        event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
