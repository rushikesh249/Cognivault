"""Model metadata, configuration schemas, and task requirements."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ProviderStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class ModelStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIGURED = "CONFIGURED"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class ModelConfig(BaseModel):
    """Declarative metadata for a single model in configs/models.yaml (TRD §13)."""
    model_id: str = Field(..., description="Unique canonical model identifier")
    display_name: Optional[str] = Field(None, description="Human-readable model name")
    role: str = Field(..., description="Primary role (general, coding, vision, etc.)")
    capabilities: List[str] = Field(default_factory=list, description="Supported capabilities")
    modalities: List[str] = Field(default_factory=lambda: ["text"], description="Supported modalities (text, image)")
    context_length: int = Field(default=8192, description="Maximum context window in tokens")
    vram_gb: Optional[float] = Field(default=None, description="VRAM required in GB")
    serving_backend: str = Field(default="ollama", description="Serving engine name")
    model_path: str = Field(..., description="Local model tag or URI")
    enabled: bool = Field(default=True, description="Whether this model is active")
    hardware_requirements: Optional[Dict[str, Any]] = Field(default=None, description="Hardware constraints")

    @field_validator("model_id", "role", "model_path")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v.strip()


class ModelRegistryFile(BaseModel):
    """Root schema for configs/models.yaml."""
    models: List[ModelConfig] = Field(default_factory=list)


class TaskRequirement(BaseModel):
    """Requirement payload passed into ModelRouter.select() (TRD §14)."""
    task_type: Optional[str] = Field(default=None, description="Task category (document, coding, vision)")
    preferred_role: Optional[str] = Field(default=None, description="Preferred model role")
    modality: str = Field(default="text", description="Required input modality")
    capabilities: List[str] = Field(default_factory=list, description="Required capabilities subset")
    max_context_needed: Optional[int] = Field(default=None, description="Minimum context length required")
    max_vram_gb: Optional[float] = Field(default=None, description="Maximum VRAM budget in GB")


class ModelInfoOut(BaseModel):
    """API representation of a model (TRD Table 19)."""
    model_id: str
    display_name: Optional[str] = None
    role: str
    capabilities: List[str]
    modalities: List[str]
    context_length: int
    vram_gb: Optional[float] = None
    serving_backend: str = "ollama"
    model_path: str
    enabled: bool
    available: bool
    status: ModelStatus
    provider_status: ProviderStatus


class ModelListOut(BaseModel):
    """Response schema for GET /api/models (TRD Table 19)."""
    models: List[ModelInfoOut] = Field(default_factory=list)
