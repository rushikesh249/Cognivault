import pytest
from pathlib import Path
from backend.app.core.config import load_settings, Settings

def test_config_loading():
    settings = load_settings()
    assert isinstance(settings, Settings)
    assert settings.app.name == "Sovereign AI Workbench"
    assert settings.app.port == 8000
    assert str(settings.paths.data_dir) == "data"
