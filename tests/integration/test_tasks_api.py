import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.persistence.db import init_db


def test_task_creation_and_retrieval_roundtrip():
    init_db()
    with TestClient(app) as client:
        # 1. Create a new task
        payload = {
            "title": "Review inspection report",
            "task_type": "document",
            "prompt": "Compare findings against Safety SOP and draft an approval note.",
            "file_ids": ["f_8a1c"],
        }
        post_resp = client.post("/api/tasks", json=payload)
        assert post_resp.status_code == 201
        post_data = post_resp.json()
        assert "task_id" in post_data
        assert post_data["status"] == "created"
        task_id = post_data["task_id"]

        # 2. Retrieve task detail
        get_resp = client.get(f"/api/tasks/{task_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["task_id"] == task_id
        assert get_data["title"] == "Review inspection report"
        assert get_data["task_type"] == "document"
        assert get_data["prompt"] == payload["prompt"]
        assert get_data["status"] == "created"


def test_get_nonexistent_task_returns_404():
    init_db()
    with TestClient(app) as client:
        resp = client.get("/api/tasks/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data


def test_create_task_invalid_type_returns_422():
    init_db()
    with TestClient(app) as client:
        payload = {
            "title": "Invalid task",
            "task_type": "unsupported_type",
            "prompt": "Test prompt",
        }
        resp = client.post("/api/tasks", json=payload)
        assert resp.status_code == 422
