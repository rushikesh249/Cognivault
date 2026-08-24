"""Integration tests for Agent Run API and SSE Event Streaming (TRD Section 9, Table 12, Table 14)."""

import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.task_repository import TaskRepository


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_agent_run_endpoint_lifecycle():
    """Verify POST /api/agent/run handles 202, 404, and 409 status codes (TRD Table 12)."""
    client = TestClient(app)

    # 1. 404 Not Found on non-existent task
    res_404 = client.post("/api/agent/run", json={"task_id": "non-existent-task-id"})
    assert res_404.status_code == 404

    # 2. Create valid task in database
    with get_db_context() as session:
        repo = TaskRepository(session)
        task = repo.create(title="SSE Test Task", task_type="document", prompt="Verify SSE streaming")
        task_id = task.task_id

    # 3. 202 Accepted on valid start
    res_202 = client.post("/api/agent/run", json={"task_id": task_id})
    assert res_202.status_code == 202
    data = res_202.json()
    assert data["task_id"] == task_id
    assert data["status"] == "running"

    # 4. 409 Conflict if task is already running
    # Force status to running in DB
    with get_db_context() as session:
        repo = TaskRepository(session)
        repo.update_status(task_id, status="running")

    res_409 = client.post("/api/agent/run", json={"task_id": task_id})
    assert res_409.status_code == 409


def test_sse_event_stream_historical_replay_and_format():
    """Verify GET /api/tasks/{task_id}/events replays past events in text/event-stream format (TRD Table 14)."""
    client = TestClient(app)

    # Create task with 3 events
    with get_db_context() as session:
        repo = TaskRepository(session)
        task = repo.create(title="Historical SSE Task", task_type="document", prompt="Test historical replay")
        task_id = task.task_id
        repo.add_event(task_id, "task_understanding", "Task understood", "info")
        repo.add_event(task_id, "planning", "Planning completed", "info")
        repo.add_event(task_id, "final_deliverable", "Workflow complete", "info")
        repo.update_status(task_id, "succeeded")

    response = client.get(f"/api/tasks/{task_id}/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    lines = response.text.split("\n\n")
    events = [json.loads(line.replace("data: ", "")) for line in lines if line.startswith("data: ")]
    
    assert len(events) >= 3
    nodes = [e["node"] for e in events]
    assert "task_understanding" in nodes
    assert "planning" in nodes
    assert "final_deliverable" in nodes
