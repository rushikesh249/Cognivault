"""Unit tests for File Upload and Ingestion API (TRD Section 9, Table 11)."""

import io
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.persistence.db import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_upload_pdf_success():
    """Verify uploading a valid PDF returns 201 Created with metadata."""
    client = TestClient(app)
    
    # Create minimal valid PDF in memory
    import fitz
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    response = client.post(
        "/api/files/upload",
        files={"file": ("test_doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_doc.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["pages"] == 1
    assert data["size_bytes"] == len(pdf_bytes)


def test_upload_unsupported_mime_type_returns_400():
    """Verify uploading an unsupported file type returns 400 Bad Request."""
    client = TestClient(app)
    response = client.post(
        "/api/files/upload",
        files={"file": ("script.py", b"print('hello')", "text/x-python")},
    )
    assert response.status_code == 400


def test_upload_magic_signature_mismatch_returns_400():
    """Verify declared PDF MIME type with non-PDF magic bytes returns 400 Bad Request."""
    client = TestClient(app)
    fake_pdf = b"NOT_A_REAL_PDF_HEADER"
    response = client.post(
        "/api/files/upload",
        files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_oversized_file_returns_413():
    """Verify file exceeding maximum upload limit (50 MB) returns 413 Payload Too Large."""
    client = TestClient(app)
    oversized = b"%PDF" + (b"0" * (51 * 1024 * 1024))  # 51 MB
    response = client.post(
        "/api/files/upload",
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 413
