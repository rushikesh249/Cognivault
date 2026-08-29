"""Agent Orchestration Service (TRD Section 8, Table 8, ADR-005, Component #4)."""

import asyncio
import logging
from typing import Optional
from pathlib import Path
import shutil
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
        max_iter = settings.agent.max_iterations.get(task_type, 6 if task_type == "coding" else (3 if task_type == "vision" else 4))

        # Ensure sandbox task workspace directory exists
        workspace_dir = Path(settings.paths.data_dir) / "sandbox" / task_id
        workspace_dir.mkdir(parents=True, exist_ok=True)

        if task_type == "coding":
            prompt_lower = (prompt or "").lower()
            if "factorial" in prompt_lower:
                # Seed factorial demo workspace if not already present
                test_files = list(workspace_dir.glob("test_*.py"))
                if not test_files:
                    initial_factorial_code = (
                        '"""Recursive Factorial Module (Hero Flow Seed).\n\n'
                        'Contains intentional edge-case defect for cyclic self-correction demonstration.\n'
                        '"""\n\n'
                        'def factorial(n: int) -> int:\n'
                        '    """Calculate factorial of n recursively."""\n'
                        '    if n < 0:\n'
                        '        raise ValueError("Factorial not defined for negative numbers")\n'
                        '    if n == 0:\n'
                        '        return 0  # Injected defect: 0! should be 1, but returns 0\n'
                        '    return n * factorial(n - 1)\n'
                    )
                    factorial_test_code = (
                        '"""Unit tests for recursive factorial implementation."""\n\n'
                        'import pytest\n'
                        'from factorial import factorial\n\n\n'
                        'def test_factorial_positive():\n'
                        '    """Verify positive integers factorial."""\n'
                        '    assert factorial(1) == 1\n'
                        '    assert factorial(3) == 6\n'
                        '    assert factorial(5) == 120\n\n\n'
                        'def test_factorial_zero():\n'
                        '    """Verify factorial of 0 is 1."""\n'
                        '    assert factorial(0) == 1\n\n\n'
                        'def test_factorial_negative():\n'
                        '    """Verify negative input raises ValueError."""\n'
                        '    with pytest.raises(ValueError):\n'
                        '        factorial(-1)\n'
                    )
                    if not (workspace_dir / "factorial.py").exists():
                        (workspace_dir / "factorial.py").write_text(initial_factorial_code, encoding="utf-8")
                    (workspace_dir / "test_factorial.py").write_text(factorial_test_code, encoding="utf-8")
            elif "telemetry" in prompt_lower or "data processor" in prompt_lower or "moving average" in prompt_lower:
                seed_src = Path("sandbox/demo_seed/data_processor.py")
                seed_test = Path("sandbox/demo_seed/test_data_processor.py")
                if seed_src.exists() and not (workspace_dir / "data_processor.py").exists():
                    shutil.copy2(seed_src, workspace_dir / "data_processor.py")
                if seed_test.exists() and not (workspace_dir / "test_data_processor.py").exists():
                    shutil.copy2(seed_test, workspace_dir / "test_data_processor.py")

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
