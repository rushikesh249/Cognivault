"""Configuration-driven Model Registry (TRD §13, ADR-003)."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from backend.app.core.config import get_project_root
from backend.app.models.exceptions import ModelConfigurationError, ModelNotFoundError
from backend.app.models.schema import ModelConfig, ModelRegistryFile

logger = logging.getLogger("sovereign_workbench.models.registry")


class ModelRegistry:
    """Thread-safe, configuration-driven registry for local open-weight models."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or (get_project_root() / "configs" / "models.yaml")
        self._models_by_id: Dict[str, ModelConfig] = {}
        self._models_by_role: Dict[str, List[ModelConfig]] = {}
        self.load()

    @property
    def config_path(self) -> Path:
        return self._config_path

    def load(self) -> None:
        """Load and validate model definitions from YAML config."""
        if not self._config_path.exists():
            logger.warning(f"Model config file not found at {self._config_path}. Initializing empty registry.")
            self._models_by_id.clear()
            self._models_by_role.clear()
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ModelConfigurationError(f"Failed to parse YAML from {self._config_path}: {e}") from e

        try:
            parsed = ModelRegistryFile(**raw_data)
        except Exception as e:
            raise ModelConfigurationError(f"Invalid model registry configuration schema: {e}") from e

        by_id: Dict[str, ModelConfig] = {}
        by_role: Dict[str, List[ModelConfig]] = {}

        for model in parsed.models:
            if model.model_id in by_id:
                raise ModelConfigurationError(
                    f"Duplicate model_id detected in {self._config_path}: '{model.model_id}'"
                )
            by_id[model.model_id] = model
            by_role.setdefault(model.role, []).append(model)

        self._models_by_id = by_id
        self._models_by_role = by_role
        logger.info(f"Loaded {len(by_id)} models from {self._config_path}")

    def reload(self) -> None:
        """Re-read models.yaml on explicit refresh without application restart."""
        self.load()

    def get_by_id(self, model_id: str) -> Optional[ModelConfig]:
        """Retrieve model configuration by exact model_id."""
        return self._models_by_id.get(model_id)

    def get_by_role(self, role: str, enabled_only: bool = True) -> List[ModelConfig]:
        """Retrieve all models configured for a specific role."""
        models = self._models_by_role.get(role, [])
        if enabled_only:
            return [m for m in models if m.enabled]
        return list(models)

    def get(self, role_or_id: str) -> Optional[ModelConfig]:
        """Lookup by exact model_id first, then primary role."""
        if role_or_id in self._models_by_id:
            return self._models_by_id[role_or_id]
        role_matches = self.get_by_role(role_or_id, enabled_only=True)
        if role_matches:
            return role_matches[0]
        return None

    def list(self, enabled_only: bool = False) -> List[ModelConfig]:
        """Return list of all registered models."""
        if enabled_only:
            return [m for m in self._models_by_id.values() if m.enabled]
        return list(self._models_by_id.values())

    def count(self) -> int:
        return len(self._models_by_id)
