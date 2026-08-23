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
    """Declarative requirement mapping for a specific task_type (TRD Section 14.1, Table 34)."""
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
    """Authoritative declarative routing configuration (TRD Section 14.1)."""
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


class EmbeddingSettings(BaseModel):
    """Embedding model configuration (TRD Section 16.1, ADR-006)."""
    model_id: str = Field(default="BAAI/bge-small-en-v1.5", description="Production embedding model identifier")
    local_model_path: Optional[str] = Field(default=None, description="Local filesystem path or cache for model weights")
    dimension: int = Field(default=384, description="Embedding vector dimension")
    allow_download: bool = Field(default=False, description="Explicit flag to allow/disallow remote weight downloads")


class ChromaSettings(BaseModel):
    """ChromaDB persistence and client configuration (TRD Section 16.1, Section 29.1)."""
    persist_directory: str = Field(default="data/chroma", description="Local directory for persistent vector store")
    anonymized_telemetry: bool = Field(default=False, description="Strictly disable telemetry for sovereignty")


class RAGSettings(BaseModel):
    """RAG pipeline parameters (TRD Section 16.3, Table 38)."""
    chunk_size: int = Field(default=800, ge=50, description="Chunk size in tokens")
    overlap: int = Field(default=120, ge=0, description="Chunk overlap in tokens")
    top_k: int = Field(default=5, ge=1, description="Number of top matches to retrieve")
    similarity_threshold: float = Field(default=0.55, ge=0.0, le=1.0, description="Cosine similarity cutoff")
    collection_name: str = Field(default="knowledge_base", description="ChromaDB collection name")
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)


class Settings(BaseModel):
    app: AppInfo = Field(default_factory=AppInfo)
    paths: AppPaths = Field(default_factory=AppPaths)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    routing: RoutingSettings = Field(default_factory=RoutingSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)


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
