"""Model layer custom exceptions."""


class ModelRegistryError(Exception):
    """Base exception for all model registry and routing errors."""
    pass


class ModelConfigurationError(ModelRegistryError):
    """Raised when model configuration is invalid, missing, or has duplicate IDs."""
    pass


class ModelNotFoundError(ModelRegistryError):
    """Raised when a requested model_id or role is not found in the registry."""
    pass


class ModelUnavailable(ModelRegistryError):
    """Raised when no suitable or available model can satisfy a task requirement."""
    pass


class ModelLoadError(ModelRegistryError):
    """Raised when a model fails to load into memory or GPU VRAM."""
    pass


class ProviderUnavailable(ModelRegistryError):
    """Raised when the local model provider (e.g., Ollama) is not running/reachable."""
    pass
