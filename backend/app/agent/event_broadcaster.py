"""Event Broadcaster and Synchronous Task Event Logging for Agent Execution (TRD Section 11.4, Table 14)."""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Set

from backend.app.persistence.db import get_db_context
from backend.app.persistence.models import TaskEventORM, get_utc_now
from backend.app.persistence.task_repository import TaskRepository

logger = logging.getLogger("sovereign_workbench.agent.events")


class EventBroadcaster:
    """In-memory event hub for Server-Sent Events (SSE) streaming per task_id."""

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """Register a subscriber queue for task_id events."""
        async with self._lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = set()
            q: asyncio.Queue = asyncio.Queue()
            self._subscribers[task_id].add(q)
            return q

    async def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """Unregister a subscriber queue."""
        async with self._lock:
            if task_id in self._subscribers:
                self._subscribers[task_id].discard(queue)
                if not self._subscribers[task_id]:
                    del self._subscribers[task_id]

    async def broadcast(self, task_id: str, event_data: Dict[str, Any]) -> None:
        """Push an event to all active subscriber queues for task_id."""
        async with self._lock:
            queues = list(self._subscribers.get(task_id, []))
        for q in queues:
            try:
                q.put_nowait(event_data)
            except Exception as e:
                logger.warning(f"Failed to queue event for subscriber on task '{task_id}': {e}")

    def log_and_emit(
        self,
        task_id: str,
        node: str,
        message: str,
        level: str = "info",
    ) -> Dict[str, Any]:
        """Synchronously persist event to SQLite (if task exists) and notify active SSE listeners."""
        with get_db_context() as session:
            repo = TaskRepository(session)
            task = repo.get_by_id(task_id)
            if task is not None:
                event = repo.add_event(
                    task_id=task_id,
                    node=node,
                    message=message,
                    level=level,
                )
                event_dict = {
                    "event_id": event.event_id,
                    "task_id": event.task_id,
                    "node": event.node,
                    "message": event.message,
                    "level": event.level,
                    "ts": event.ts.isoformat(),
                }
            else:
                # Standalone test state with non-persisted task_id
                event_dict = {
                    "event_id": str(uuid.uuid4()),
                    "task_id": task_id,
                    "node": node,
                    "message": message,
                    "level": level,
                    "ts": get_utc_now().isoformat(),
                }

        # Try to broadcast in current event loop if one is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(task_id, event_dict))
        except RuntimeError:
            pass

        return event_dict


# Global singleton event broadcaster
_global_event_broadcaster: Optional[EventBroadcaster] = None


def get_event_broadcaster() -> EventBroadcaster:
    global _global_event_broadcaster
    if _global_event_broadcaster is None:
        _global_event_broadcaster = EventBroadcaster()
    return _global_event_broadcaster
