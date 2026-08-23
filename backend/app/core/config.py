import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


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


class TaskRequirementConfig(BaseModel):
    """Declarative requirement mapping for a specific task_type (TRD §14.1, Table 34)."""
    preferred_role: str = Field(..., description="Preferred model role for this task type")
    capabilities: List[str] = Field(default_factory=list, description="Required model capability subset")
    modality: str = Field(default="text", description="Input modality required (text, image)")

    @field_validator("preferred_role", "modality")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v.strip()


class RoutingSettings(BaseModel):
    """Authoritative declarative routing configuration (TRD §14.1)."""
    task_requirements: Dict[str, TaskRequirementConfig] = Field(
        default_factory=lambda: {
            "document": TaskRequirementConfig(
                preferred_role="general",
                capabilities=["reasoning", "document_analysis"],
                modality="text",
            ),
            "coding": TaskRequirementConfig(
                preferred_role="coding",
                capabilities=["coding", "debugging", "testing"],
                modality="text",
            ),
            "vision": TaskRequirementConfig(
                preferred_role="vision",
                capabilities=["image_analysis"],
                modality="image",
            ),
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
    except Exception as e:
        raise RuntimeError(f"Failed to load application settings from {config_path}: {e}") from e


settings = load_settings()
