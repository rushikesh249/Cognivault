"""Unit tests for Artifact Retrieval and Metadata API (TRD Section 9, Table 18)."""

import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.task_repository import TaskRepository


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_get_artifact_binary_download_200(tmp_path):
    """Verify GET /api/artifacts/{id} downloads the generated binary artifact."""
    client = TestClient(app)
    art_id = str(uuid.uuid4())
    dummy_file = tmp_path / f"{art_id}.docx"
    dummy_file.write_bytes(b"PK\x03\x04DUMMY_DOCX_BYTES")

    with get_db_context() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(title="Test Task", task_type="document", prompt="Test")
        art_repo = ArtifactRepository(session)
        art_repo.create(
            task_id=task.task_id,
            kind="docx",
            title="Approval Note",
            storage_path=str(dummy_file),
            sources=["Safety SOP - Section 4 (p.10)"],
            artifact_id=art_id,
        )

    response = client.get(f"/api/artifacts/{art_id}")
    assert response.status_code == 200
    assert response.content == b"PK\x03\x04DUMMY_DOCX_BYTES"
    assert "wordprocessingml" in response.headers["content-type"]


def test_get_artifact_meta_query_param_200(tmp_path):
    """Verify GET /api/artifacts/{id}?meta=true returns JSON metadata with sources."""
    client = TestClient(app)
    art_id = str(uuid.uuid4())
    dummy_file = tmp_path / f"{art_id}.docx"
    dummy_file.write_bytes(b"PK\x03\x04DUMMY_DOCX_BYTES")

    with get_db_context() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(title="Test Task", task_type="document", prompt="Test")
        art_repo = ArtifactRepository(session)
        art_repo.create(
            task_id=task.task_id,
            kind="docx",
            title="Approval Note",
            storage_path=str(dummy_file),
            sources=["Safety SOP - Section 4.2 (p.12)", "Maintenance Manual - Section 8 (p.34)"],
            artifact_id=art_id,
        )

    response = client.get(f"/api/artifacts/{art_id}?meta=true")
    assert response.status_code == 200
    data = response.json()
    assert data["artifact_id"] == art_id
    assert data["kind"] == "docx"
    assert len(data["sources"]) == 2
    assert "Safety SOP - Section 4.2 (p.12)" in data["sources"]


def test_get_artifact_not_found_returns_404():
    """Verify GET /api/artifacts/{non_existent_id} returns 404 Not Found."""
    client = TestClient(app)
    response = client.get("/api/artifacts/non-existent-artifact-id-12345")
    assert response.status_code == 404


def test_get_artifact_missing_on_disk_returns_410():
    """Verify GET /api/artifacts/{id} returns 410 Gone when DB record exists but file is missing."""
    client = TestClient(app)
    art_id = str(uuid.uuid4())
    missing_file = Path("data/outputs/missing_deleted_file.docx")

    with get_db_context() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(title="Test Task", task_type="document", prompt="Test")
        art_repo = ArtifactRepository(session)
        art_repo.create(
            task_id=task.task_id,
            kind="docx",
            title="Ghost Note",
            storage_path=str(missing_file),
            sources=[],
            artifact_id=art_id,
        )

    response = client.get(f"/api/artifacts/{art_id}")
    assert response.status_code == 410
    assert "missing" in response.json()["detail"].lower()


def test_list_artifacts_endpoint(tmp_path):
    """Verify GET /api/artifacts returns list of registered artifacts."""
    client = TestClient(app)
    response = client.get("/api/artifacts?limit=10&offset=0")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
