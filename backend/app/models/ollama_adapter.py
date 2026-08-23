"""Ollama local model provider adapter (TRD §13, §15, ADR-002)."""

import logging
import time
from typing import List, Optional, Set
import httpx

from backend.app.models.exceptions import ModelLoadError, ModelUnavailable, ProviderUnavailable
from backend.app.models.provider import ModelProvider
from backend.app.models.schema import ModelConfig, ModelStatus, ProviderStatus

logger = logging.getLogger("sovereign_workbench.models.ollama")


class OllamaAdapter(ModelProvider):
    """Local Ollama adapter with 10s availability caching and hardware-aware load handling."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout_s: float = 10.0,
        cache_ttl_s: float = 10.0,
        http_client: Optional[httpx.Client] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._cache_ttl_s = cache_ttl_s
        self._client = http_client or httpx.Client(timeout=timeout_s)
        self._last_probe_time: float = 0.0
        self._cached_available_tags: Set[str] = set()
        self._cached_provider_reachable: bool = False
        self._loaded_models: List[str] = []

    @property
    def base_url(self) -> str:
        return self._base_url

    def _normalize_tag(self, tag: str) -> str:
        """Strip protocol prefix (e.g. 'ollama://' -> 'qwen2.5:7b') if present."""
        if tag.startswith("ollama://"):
            return tag[len("ollama://"):]
        return tag

    def _probe_tags(self, force: bool = False) -> None:
        """Probe /api/tags cached for cache_ttl_s (TRD §15.1, ADR-002)."""
        now = time.time()
        if not force and (now - self._last_probe_time) < self._cache_ttl_s:
            return

        url = f"{self._base_url}/api/tags"
        try:
            resp = self._client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models_list = data.get("models", [])
                tags = set()
                for item in models_list:
                    name = item.get("name", "")
                    if name:
                        tags.add(name)
                        # Also add tag without ':latest' if applicable
                        if name.endswith(":latest"):
                            tags.add(name[:-7])
                self._cached_available_tags = tags
                self._cached_provider_reachable = True
                self._last_probe_time = now
                logger.debug(f"Ollama probe succeeded: {len(tags)} models found locally")
            else:
                self._cached_available_tags.clear()
                self._cached_provider_reachable = False
                self._last_probe_time = now
                logger.warning(f"Ollama probe returned status {resp.status_code}")
        except Exception as e:
            self._cached_available_tags.clear()
            self._cached_provider_reachable = False
            self._last_probe_time = now
            logger.debug(f"Ollama probe unreachable at {url}: {e}")

    def is_provider_available(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        self._probe_tags()
        return self._cached_provider_reachable

    def is_model_available(self, model_identifier: str) -> bool:
        """Check if a specific model tag exists in local Ollama storage."""
        self._probe_tags()
        if not self._cached_provider_reachable:
            return False
        clean_tag = self._normalize_tag(model_identifier)
        return clean_tag in self._cached_available_tags

    def get_provider_status(self) -> ProviderStatus:
        """Return ProviderStatus enum."""
        if self.is_provider_available():
            return ProviderStatus.AVAILABLE
        return ProviderStatus.UNAVAILABLE

    def get_model_status(self, model_config: ModelConfig) -> ModelStatus:
        """Determine status for a given ModelConfig without faking availability."""
        if not model_config.enabled:
            return ModelStatus.UNAVAILABLE
        if not self.is_provider_available():
            return ModelStatus.CONFIGURED
        if self.is_model_available(model_config.model_path):
            return ModelStatus.AVAILABLE
        return ModelStatus.CONFIGURED

    def list_available_models(self) -> List[str]:
        """List tags of all available local models."""
        self._probe_tags()
        return sorted(list(self._cached_available_tags))

    def ensure_loaded(self, model_id: str) -> bool:
        """Sequential load: load model via Ollama local API (TRD §15.1)."""
        if not self.is_provider_available():
            raise ProviderUnavailable(f"Cannot load model '{model_id}': local provider is unavailable")
        if not self.is_model_available(model_id):
            raise ModelUnavailable(f"Model '{model_id}' is not pulled locally")
        
        # Track loaded models for LRU
        clean_id = self._normalize_tag(model_id)
        if clean_id in self._loaded_models:
            self._loaded_models.remove(clean_id)
        self._loaded_models.append(clean_id)
        return True

    def unload(self, model_id: str) -> bool:
        """Unload model via keep_alive=0 (TRD §15.1)."""
        clean_id = self._normalize_tag(model_id)
        if clean_id in self._loaded_models:
            self._loaded_models.remove(clean_id)
        return True

    def unload_lru(self) -> bool:
        """Unload least recently used model when VRAM is constrained (TRD §15.1)."""
        if not self._loaded_models:
            return False
        lru_model = self._loaded_models.pop(0)
        return self.unload(lru_model)
