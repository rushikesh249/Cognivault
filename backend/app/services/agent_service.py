"""Agent Orchestration Service (TRD Section 8, Table 8, ADR-005, Component #4)."""

import asyncio
import logging
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.agent.graph import agent_graph
from backend.app.agent.state import AgentState
from backend.app.core.config import settings
from backend.app.persistence.db import get_db_context
from backend.app.persistence.task_repository import TaskRepository

logger = logging.getLogger("sovereign_workbench.services.agent")


class TaskNotFoundError(Exception):
    """Raised when task_id does not exist."""
    pass


class TaskAlreadyRunningError(Exception):
    """Raised when task is already in running state."""
    pass


class AgentService:
    """Service to orchestrate background LangGraph agent workflows."""

    def __init__(self):
        pass

    def start_task(self, task_id: str) -> None:
        """Atomically lock task and launch agent graph in background loop."""
        with get_db_context() as session:
            repo = TaskRepository(session)
            task = repo.get_by_id(task_id)
            if not task:
                raise TaskNotFoundError(f"Task '{task_id}' not found.")

            if task.status == "running":
                raise TaskAlreadyRunningError(f"Task '{task_id}' is already running.")

            # Atomically set status to running
            repo.update_status(task_id, status="running")

        # Launch background task
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._run_graph_async(task_id))
        except RuntimeError:
            # Synchronous invocation fallback (e.g. within unit tests)
            self._run_graph_sync(task_id)

    async def _run_graph_async(self, task_id: str) -> AgentState:
        """Run agent graph asynchronously inside event loop."""
        return await asyncio.to_thread(self._run_graph_sync, task_id)

    def _run_graph_sync(self, task_id: str) -> AgentState:
        """Synchronously execute LangGraph workflow for task_id."""
        with get_db_context() as session:
            repo = TaskRepository(session)
            task = repo.get_by_id(task_id)
            if not task:
                raise TaskNotFoundError(f"Task '{task_id}' not found.")
            task_type = task.task_type
            prompt = task.prompt

        # Determine configured max_iterations
        max_iter = settings.agent.max_iterations.get(task_type, 4)

        initial_state: AgentState = {
            "task_id": task_id,
            "task_type": task_type,
            "goal": prompt,
            "plan": [],
            "current_step_index": 0,
            "iteration": 0,
            "max_iterations": max_iter,
            "selected_model_id": None,
            "tool_calls": [],
            "observations": [],
            "validation_passed": False,
            "validation_notes": None,
            "final_artifact_id": None,
            "status": "running",
            "error": None,
        }

        logger.info(f"Starting agent state graph execution for task '{task_id}' (max_iterations: {max_iter})")

        try:
            final_state = agent_graph.invoke(initial_state, config={"recursion_limit": 100})
            logger.info(f"Agent state graph finished for task '{task_id}' with status='{final_state.get('status')}'")
            return final_state
        except Exception as e:
            logger.error(f"Fatal error executing agent graph for task '{task_id}': {e}", exc_info=True)
            with get_db_context() as session:
                repo = TaskRepository(session)
                repo.update_status(task_id, status="failed")
                repo.add_event(task_id, node="agent", message=f"Fatal agent error: {e}", level="error")
            raise


# Global singleton
_global_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _global_agent_service
    if _global_agent_service is None:
        _global_agent_service = AgentService()
    return _global_agent_service
