import pytest

def test_backend_imports():
    from backend.app.main import app, create_app
    from backend.app.core.config import settings, load_settings
    from backend.app.core.logging import setup_logging
    from backend.app.api.health import router as health_router

    assert app is not None
    assert callable(create_app)
    assert settings.app.name == "Sovereign AI Workbench"
