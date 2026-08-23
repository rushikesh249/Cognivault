import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field


class AppInfo(BaseModel):
    name: str = "Sovereign AI Workbench"
    version: str = "0.1.0"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000


class AppPaths(BaseModel):
    data_dir: Path = Path("data")
    uploads_dir: Path = Path("data/uploads")
    outputs_dir: Path = Path("data/outputs")
    logs_dir: Path = Path("data/logs")
    models_dir: Path = Path("models")
    knowledge_base_dir: Path = Path("knowledge_base")


class OllamaSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 11434
    timeout_s: float = 10.0
    cache_ttl_s: float = 10.0

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class RoutingSettings(BaseModel):
    task_role_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "document": "general",
            "coding": "coding",
            "vision": "vision",
        }
    )


class Settings(BaseModel):
    app: AppInfo = Field(default_factory=AppInfo)
    paths: AppPaths = Field(default_factory=AppPaths)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    routing: RoutingSettings = Field(default_factory=RoutingSettings)


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def load_settings(config_path: Optional[Path] = None) -> Settings:
    root = get_project_root()
    if config_path is None:
        config_path = root / "configs" / "app.yaml"

    if not config_path.exists():
        return Settings()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = yaml.safe_load(f) or {}
        return Settings(**data)
    except Exception:
        return Settings()


settings = load_settings()
