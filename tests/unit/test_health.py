import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Sovereign AI Workbench"
    assert "version" in data
