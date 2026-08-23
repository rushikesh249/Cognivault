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


class SandboxSettings(BaseModel):
    """Docker Sandbox execution parameters (TRD Section 20, Section 23, ADR-008)."""
    image_name: str = Field(default="sovereign-sandbox:latest", description="Sandbox Docker image tag")
    cpu_limit: float = Field(default=1.0, ge=0.1, le=4.0, description="Max CPU cores per container")
    memory_limit: str = Field(default="512m", description="Max memory per container")
    timeout_s: int = Field(default=30, ge=1, le=120, description="Default execution timeout in seconds")
    network: str = Field(default="none", description="Container network isolation mode (must be 'none')")
    pids_limit: int = Field(default=64, description="Max process limit inside container")
    max_output_bytes: int = Field(default=1048576, description="Max bytes to capture for stdout/stderr (1 MB)")


class AgentSettings(BaseModel):
    """LangGraph Agent configuration (TRD Section 11.4, ADR-005)."""
    max_iterations: Dict[str, int] = Field(
        default_factory=lambda: {
            "document": 4,
            "coding": 6,
            "vision": 3,
        },
        description="Max iterations per task_type before bounded failure",
    )


class OCRSettings(BaseModel):
    """OCR Service configuration (TRD Section 17, Section 30)."""
    dpi: int = Field(default=300, ge=72, le=600, description="Rasterization DPI for scanned page rendering")
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Threshold below which OCR page is flagged low confidence")


class UploadSettings(BaseModel):
    """File upload limits and validation (TRD Table 11)."""
    max_upload_bytes: int = Field(default=10485760, description="Max allowed upload file size (10 MB)")
    allowed_mime_types: List[str] = Field(
        default_factory=lambda: ["application/pdf", "image/jpeg", "image/png"],
        description="Permitted MIME types for upload",
    )


class Settings(BaseModel):
    app: AppInfo = Field(default_factory=AppInfo)
    paths: AppPaths = Field(default_factory=AppPaths)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    routing: RoutingSettings = Field(default_factory=RoutingSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    ocr: OCRSettings = Field(default_factory=OCRSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)


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
