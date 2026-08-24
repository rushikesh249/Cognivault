"""Unit tests for Vision API Router POST /api/vision/analyze (TRD ?9, Table 16)."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.api.vision import router as vision_router
from backend.app.core.config import settings
from backend.app.multimodal.vision_service import VisionModelUnavailableError, VisionResult, VisionService
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.file_repository import FileRepository
from backend.app.services.vision_service import VisionAppService, get_vision_app_service


@pytest.fixture
def api_client(tmp_path: Path):
    init_db()
    app = FastAPI()
    app.include_router(vision_router)
    return TestClient(app)


@pytest.fixture
def registered_image_file(tmp_path: Path) -> str:
    img_dir = settings.paths.uploads_dir
    img_dir.mkdir(parents=True, exist_ok=True)
    img_file = img_dir / "test_weld_api.jpg"
    img = Image.new("RGB", (64, 64), color=(200, 100, 50))
    img.save(img_file, format="JPEG")

    file_id = "vis-test-file-01"
    with get_db_context() as session:
        repo = FileRepository(session)
        # Clean existing if present
        existing = repo.get_by_id(file_id)
        if not existing:
            repo.create(
                file_id=file_id,
                filename="test_weld_api.jpg",
                mime_type="image/jpeg",
                size_bytes=img_file.stat().st_size,
                storage_path=str(img_file),
            )
    return file_id


def test_vision_analyze_endpoint_success_200(api_client: TestClient, registered_image_file: str, monkeypatch):
    """Verify POST /api/vision/analyze returns 200 OK with valid VisionResult."""
    expected_result = VisionResult(
        observation=["Corrosion spot at bottom weld"],
        interpretation=["Surface rust due to moisture"],
        uncertainty=["Lighting reflection caveats"],
        model_used="local-vision-model",
    )

    mock_app_service = MagicMock(spec=VisionAppService)
    mock_app_service.analyze_file.return_value = expected_result

    from backend.app.api.vision import get_vision_app_service
    api_client.app.dependency_overrides[get_vision_app_service] = lambda: mock_app_service

    resp = api_client.post("/api/vision/analyze", json={"file_id": registered_image_file, "prompt": "Inspect flange"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["observation"] == ["Corrosion spot at bottom weld"]
    assert data["model_used"] == "local-vision-model"


def test_vision_analyze_file_not_found_404(api_client: TestClient):
    """Verify POST /api/vision/analyze returns 404 for non-existent file_id."""
    api_client.app.dependency_overrides.clear()
    resp = api_client.post("/api/vision/analyze", json={"file_id": "non_existent_file_9999"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_vision_analyze_invalid_mime_400(api_client: TestClient, tmp_path: Path):
    """Verify POST /api/vision/analyze returns 400 when uploaded file is a PDF."""
    api_client.app.dependency_overrides.clear()
    pdf_dir = settings.paths.uploads_dir
    pdf_file = pdf_dir / "test_doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy pdf content")

    file_id = "pdf-file-for-vision"
    with get_db_context() as session:
        repo = FileRepository(session)
        existing = repo.get_by_id(file_id)
        if not existing:
            repo.create(
                file_id=file_id,
                filename="test_doc.pdf",
                mime_type="application/pdf",
                size_bytes=len(b"%PDF-1.4 dummy pdf content"),
                storage_path=str(pdf_file),
            )

    resp = api_client.post("/api/vision/analyze", json={"file_id": file_id})
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["detail"].lower()


def test_vision_analyze_empty_payload_422(api_client: TestClient):
    """Verify POST /api/vision/analyze returns 422 for empty file_id."""
    resp = api_client.post("/api/vision/analyze", json={"file_id": ""})
    assert resp.status_code == 422


def test_vision_analyze_model_unavailable_503(api_client: TestClient, registered_image_file: str):
    """Verify POST /api/vision/analyze returns 503 when vision model is unavailable."""
    mock_app_service = MagicMock(spec=VisionAppService)
    mock_app_service.analyze_file.side_effect = VisionModelUnavailableError("Model not loaded")

    from backend.app.api.vision import get_vision_app_service
    api_client.app.dependency_overrides[get_vision_app_service] = lambda: mock_app_service

    resp = api_client.post("/api/vision/analyze", json={"file_id": registered_image_file})
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()
