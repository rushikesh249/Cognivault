"""Abstract base interface for local model providers."""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.app.models.schema import ModelConfig, ModelStatus, ProviderStatus


class ModelProvider(ABC):
    """Abstract interface for local model serving engines (Ollama, etc.)."""

    @abstractmethod
    def is_provider_available(self) -> bool:
        """Check if the underlying local model server is reachable."""
        pass

    @abstractmethod
    def is_model_available(self, model_identifier: str) -> bool:
        """Check if a specific model tag/path is downloaded and available locally."""
        pass

    @abstractmethod
    def get_provider_status(self) -> ProviderStatus:
        """Return detailed provider reachability status."""
        pass

    @abstractmethod
    def get_model_status(self, model_config: ModelConfig) -> ModelStatus:
        """Evaluate the availability status of a configured model."""
        pass

    @abstractmethod
    def list_available_models(self) -> List[str]:
        """List all model tags currently present in the local provider."""
        pass

    @abstractmethod
    def ensure_loaded(self, model_id: str) -> bool:
        """Ensure the model is loaded in memory/VRAM before inference (TRD §15.1)."""
        pass

    @abstractmethod
    def unload(self, model_id: str) -> bool:
        """Unload a model from memory/VRAM."""
        pass

    @abstractmethod
    def unload_lru(self) -> bool:
        """Unload the least recently used model when VRAM is constrained (TRD §15.1)."""
        pass
