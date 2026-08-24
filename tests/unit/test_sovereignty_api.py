"""Unit tests for GET /api/sovereignty/status (TRD ?9, Table 20)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.sovereignty import router as sovereignty_router
from backend.app.persistence.db import init_db
from backend.app.services.sovereignty_service import SovereigntyAppService, get_sovereignty_app_service
from backend.app.sovereignty.adapters.stub import StubNetworkAdapter
from backend.app.sovereignty.events import SovereigntyStatus
from backend.app.sovereignty.monitor import SovereigntyMonitor


@pytest.fixture
def client():
    init_db()
    app = FastAPI()
    app.include_router(sovereignty_router)
    return TestClient(app)


def test_get_sovereignty_status_200(client: TestClient):
    """Verify GET /api/sovereignty/status returns 200 with complete SovereigntyStatus schema."""
    resp = client.get("/api/sovereignty/status")
    assert resp.status_code == 200
    data = resp.json()

    # Validate all 10 required TRD Table 20 top-level fields
    assert "external_ai_calls" in data
    assert "external_embedding_calls" in data
    assert "external_ocr_calls" in data
    assert "data_egress_mb" in data
    assert data["local_inference"] in ("ok", "degraded")
    assert data["local_ocr"] in ("ok", "degraded")
    assert data["local_rag"] in ("ok", "degraded")
    assert data["local_vision"] in ("ok", "degraded")
    assert data["local_sandbox"] in ("ok", "degraded")
    assert data["monitor_status"] in ("ok", "degraded")

    # Validate supplementary monitoring fields (ADR-012)
    assert "byte_accounting_supported" in data
    assert isinstance(data["byte_accounting_supported"], bool)
    assert "external_connections_5m" in data
    assert isinstance(data["external_connections_5m"], int)
    assert "external_dns_lookups_5m" in data
    assert isinstance(data["external_dns_lookups_5m"], int)

    # Verify NO nested 'subsystems' key — all fields are top-level
    assert "subsystems" not in data


def test_subsystem_health_reporting_with_mock_service(client: TestClient):
    """Verify SovereigntyStatus returns degraded when monitor detects external events."""
    mock_status = SovereigntyStatus(
        external_ai_calls=1,
        external_embedding_calls=0,
        external_ocr_calls=0,
        data_egress_mb=0.05,
        local_inference="ok",
        local_ocr="ok",
        local_rag="ok",
        local_vision="ok",
        local_sandbox="ok",
        monitor_status="degraded",
        byte_accounting_supported=False,
        external_connections_5m=1,
        external_dns_lookups_5m=0,
    )

    class MockSovereigntyService:
        def get_status(self, window_minutes: int = 5):
            return mock_status

    client.app.dependency_overrides[get_sovereignty_app_service] = lambda: MockSovereigntyService()

    resp = client.get("/api/sovereignty/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["external_ai_calls"] == 1
    assert data["monitor_status"] == "degraded"
    assert data["byte_accounting_supported"] is False
    assert data["external_connections_5m"] == 1
    assert data["external_dns_lookups_5m"] == 0
    # All fields are top-level, no nested subsystems
    assert "subsystems" not in data
