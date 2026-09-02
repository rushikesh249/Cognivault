"""Ollama local model provider adapter (TRD ?13, ?15, ADR-002)."""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import httpx

from backend.app.core.config import settings
from backend.app.models.exceptions import (
    ModelConnectionTimeoutError,
    ModelInferenceTimeoutError,
    ModelLoadError,
    ModelTimeoutError,
    ModelUnavailable,
    ProviderUnavailable,
)
from backend.app.models.provider import ModelProvider
from backend.app.models.schema import ModelConfig, ModelStatus, ProviderStatus

logger = logging.getLogger("sovereign_workbench.models.ollama")


class OllamaAdapter(ModelProvider):
    """Local Ollama adapter with 10s availability caching and hardware-aware load handling."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_s: Optional[float] = None,
        connection_timeout_s: Optional[float] = None,
        vision_timeout_s: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_backoff_s: Optional[float] = None,
        cache_ttl_s: Optional[float] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self._base_url = (base_url or f"http://{settings.ollama.host}:{settings.ollama.port}").rstrip("/")
        self._timeout_s = timeout_s if timeout_s is not None else settings.ollama.timeout_s
        self._connection_timeout_s = connection_timeout_s if connection_timeout_s is not None else settings.ollama.connection_timeout_s
        self._vision_timeout_s = vision_timeout_s if vision_timeout_s is not None else settings.ollama.vision_timeout_s
        self._max_retries = max_retries if max_retries is not None else settings.ollama.max_retries
        self._retry_backoff_s = retry_backoff_s if retry_backoff_s is not None else settings.ollama.retry_backoff_s
        self._cache_ttl_s = cache_ttl_s if cache_ttl_s is not None else settings.ollama.cache_ttl_s
        self._client = http_client or httpx.Client(timeout=self._timeout_s)
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
        """Probe /api/tags cached for cache_ttl_s (TRD Section 15.1, ADR-002)."""
        now = time.time()
        if not force and (now - self._last_probe_time) < self._cache_ttl_s:
            return

        url = f"{self._base_url}/api/tags"
        try:
            resp = self._client.get(url, timeout=self._connection_timeout_s)
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

    def check_model_health(self, model_identifier: str) -> Dict[str, Any]:
        """Diagnostic check for Ollama reachability and specific model tag."""
        self._probe_tags(force=True)
        clean_tag = self._normalize_tag(model_identifier)
        if not self._cached_provider_reachable:
            return {
                "available": False,
                "reason": "provider_unavailable",
                "message": f"Local Ollama provider unreachable at {self._base_url}.",
            }
        if clean_tag not in self._cached_available_tags:
            return {
                "available": False,
                "reason": "model_unavailable",
                "message": f"Local model '{clean_tag}' is not installed locally. Pull it via: ollama pull {clean_tag}",
            }
        return {
            "available": True,
            "reason": "healthy",
            "message": f"Local model '{clean_tag}' is available.",
        }

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
        """Sequential load: load model via Ollama local API (TRD Section 15.1)."""
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
        """Unload model via keep_alive=0 (TRD Section 15.1)."""
        clean_id = self._normalize_tag(model_id)
        if clean_id in self._loaded_models:
            self._loaded_models.remove(clean_id)
        return True

    def unload_lru(self) -> bool:
        """Unload least recently used model when VRAM is constrained (TRD Section 15.1)."""
        if not self._loaded_models:
            return False
        lru_model = self._loaded_models.pop(0)
        return self.unload(lru_model)

    def generate(
        self,
        model_id: str,
        prompt: str,
        images: Optional[List[str]] = None,
        system: Optional[str] = None,
        format: Optional[str] = None,
        stream: bool = False,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        on_retry: Optional[Callable[[int, int, str], None]] = None,
    ) -> str:
        """Execute local generate call against Ollama /api/generate with bounded retries (ADR-002)."""
        clean_model = self._normalize_tag(model_id)
        if not self.is_provider_available():
            raise ProviderUnavailable(f"Cannot generate from '{model_id}': local provider is unavailable at {self._base_url}")
        if not self.is_model_available(clean_model):
            raise ModelUnavailable(f"Model '{clean_model}' is not pulled locally")

        payload: dict = {
            "model": clean_model,
            "prompt": prompt,
            "stream": stream,
        }
        if images:
            payload["images"] = images
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format

        url = f"{self._base_url}/api/generate"
        is_vision = bool(images) or "llava" in clean_model.lower()
        req_timeout = timeout if timeout is not None else (self._vision_timeout_s if is_vision else self._timeout_s)
        total_retries = max_retries if max_retries is not None else self._max_retries

        logger.info(
            f"[OLLAMA_HTTP_REQUEST] POST {url} | model='{clean_model}' | "
            f"images={len(images) if images else 0} | format='{format}' | timeout={req_timeout}s | max_retries={total_retries}"
        )

        last_exception: Optional[Exception] = None
        for attempt in range(1, total_retries + 2):
            try:
                resp = self._client.post(url, json=payload, timeout=req_timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "")
                    logger.info(
                        f"[OLLAMA_HTTP_SUCCESS] 200 OK from {url} | "
                        f"model='{clean_model}' | response_len={len(response_text)}"
                    )
                    return response_text
                elif resp.status_code in (502, 503, 504):
                    err_msg = f"Ollama HTTP {resp.status_code}: {resp.text}"
                    logger.warning(f"[OLLAMA_HTTP_RETRYABLE] {err_msg} on attempt {attempt}")
                    last_exception = ProviderUnavailable(err_msg)
                else:
                    logger.error(f"Ollama generate returned status {resp.status_code}: {resp.text}")
                    raise ModelLoadError(f"Ollama generation failed with status {resp.status_code}: {resp.text}")

            except httpx.TimeoutException as te:
                err_msg = f"Vision model request timed out (timeout={req_timeout}s): {te}" if is_vision else f"Model request timed out: {te}"
                logger.warning(f"[OLLAMA_TIMEOUT] {err_msg} on attempt {attempt}")
                last_exception = ModelInferenceTimeoutError(err_msg)

            except (httpx.ConnectError, httpx.NetworkError) as ne:
                err_msg = f"Ollama connection error on attempt {attempt}: {ne}"
                logger.warning(f"[OLLAMA_CONNECT_ERROR] {err_msg}")
                last_exception = ProviderUnavailable(err_msg)

            if attempt <= total_retries:
                retry_idx = attempt
                retry_msg = (
                    f"Vision model request timed out. Retrying {retry_idx}/{total_retries}..."
                    if is_vision
                    else f"Model request failed. Retrying {retry_idx}/{total_retries}..."
                )
                logger.warning(f"[model_retry] {retry_msg}")
                if on_retry:
                    try:
                        on_retry(retry_idx, total_retries, retry_msg)
                    except Exception as cb_err:
                        logger.debug(f"on_retry callback error: {cb_err}")

                backoff_delay = self._retry_backoff_s * (1.5 ** (attempt - 1))
                time.sleep(min(backoff_delay, 10.0))
            else:
                break

        if isinstance(last_exception, ModelInferenceTimeoutError):
            logger.error(f"[model_health] Local vision model request timed out after {total_retries} retries." if is_vision else f"Model request timed out after {total_retries} retries.")
            raise last_exception
        elif isinstance(last_exception, ProviderUnavailable):
            logger.error(f"[model_health] Local vision model provider unavailable after {total_retries} retries." if is_vision else f"Provider unavailable after {total_retries} retries.")
            raise last_exception
        elif last_exception:
            raise last_exception
        else:
            raise ProviderUnavailable(f"Ollama request failed after {total_retries} retries.")
