"""Vision domain service for local Vision-Language Model (VLM) image analysis (TRD ?18, PRD ?13, ADR-007)."""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.models.exceptions import (
    ModelInferenceTimeoutError,
    ModelTimeoutError,
    ModelUnavailable,
    ProviderUnavailable,
)
from backend.app.models.ollama_adapter import OllamaAdapter
from backend.app.models.provider import ModelProvider

logger = logging.getLogger("sovereign_workbench.multimodal.vision")

FORBIDDEN_VERDICT_PATTERNS = [
    r"certified\s+inspection\s+verdict",
    r"certified\s+engineering\s+diagnosis",
    r"certified\s+inspection",
    r"certified\s+verdict",
    r"official\s+certification\s+granted",
    r"statutory\s+compliance\s+guaranteed",
]


class VisionResult(BaseModel):
    """Structured response schema for multimodal vision findings (TRD Section 18.1, Table 16)."""
    observation: List[str] = Field(..., description="What is visibly present with zero inference")
    interpretation: List[str] = Field(default_factory=list, description="AI engineering hypothesis or reading")
    uncertainty: List[str] = Field(default_factory=list, description="Explicit hedges and limitations")
    model_used: str = Field(..., description="Model ID used for vision inference")


class VisionServiceError(Exception):
    """Base exception for vision service errors."""
    pass


class VisionModelUnavailableError(VisionServiceError):
    """Raised when the configured local VLM is unavailable or unreachable."""
    pass


class VisionTimeoutError(VisionServiceError):
    """Raised when VLM inference times out."""
    pass


class VisionInvalidImageError(VisionServiceError):
    """Raised when the input image file is invalid, missing, or unsupported."""
    pass


class VisionOutputValidationError(VisionServiceError):
    """Raised when VLM output fails schema validation or contains forbidden certified claims."""
    pass


VISION_SYSTEM_PROMPT = (
    "You are a sovereign industrial equipment vision inspection assistant. "
    "Analyze the provided equipment photograph or engineering image with rigorous physical objectivity.\n"
    "HARD CONSTRAINTS:\n"
    "1. STRICT OBSERVATION VS INFERENCE SEPARATION:\n"
    '   - "observation": list strictly direct, visible physical attributes discernible from the image pixels '
    '(e.g., visible components, geometry, surface colors, visible oxidation, coating condition, fluid presence). '
    'Do NOT jump to operational conclusions, failure verdicts, or maintenance judgments in this list.\n'
    '   - "interpretation": conservative engineering hypotheses or interpretations derived from the direct observations '
    '(e.g., visible surface corrosion may indicate prolonged environmental exposure; non-destructive examination recommended).\n'
    '   - "uncertainty": explicit physical, optical, and situational limitations (e.g., camera resolution, lighting angles, unobservable internal surfaces).\n'
    "2. NEVER state, imply, or claim a certified engineering inspection verdict, official diagnostic certification, or statutory guarantee.\n"
    "3. Structure your output strictly as a single JSON object with exact keys: 'observation', 'interpretation', 'uncertainty'.\n"
    "4. Do not include markdown code block backticks outside the JSON or conversational preamble."
)


class VisionService:
    """Domain service for local multimodal VLM analysis."""

    def __init__(self, provider: Optional[ModelProvider] = None):
        self._provider = provider or OllamaAdapter(
            base_url=f"http://{settings.ollama.host}:{settings.ollama.port}",
            timeout_s=settings.ollama.timeout_s,
            cache_ttl_s=settings.ollama.cache_ttl_s,
        )

    def encode_image(self, image_path: Path) -> str:
        """Read and Base64-encode an image from disk."""
        if not image_path.exists():
            raise VisionInvalidImageError(f"Image file not found: {image_path}")
        if not image_path.is_file():
            raise VisionInvalidImageError(f"Image path is not a file: {image_path}")

        try:
            with open(image_path, "rb") as f:
                content = f.read()
            if not content:
                raise VisionInvalidImageError(f"Image file is empty: {image_path}")
            return base64.b64encode(content).decode("utf-8")
        except Exception as e:
            if isinstance(e, VisionInvalidImageError):
                raise
            raise VisionInvalidImageError(f"Failed to read image '{image_path}': {e}") from e

    def parse_and_validate_output(self, raw_output: str, model_used: str) -> VisionResult:
        """Parse raw VLM output into a validated VisionResult instance."""
        if not raw_output or not raw_output.strip():
            raise VisionOutputValidationError("VLM returned an empty response.")

        text = raw_output.strip()

        # Check for and reject/sanitize forbidden certified verdict claims (TRD ?18)
        for pattern in FORBIDDEN_VERDICT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Forbidden certified verdict phrase matched pattern '{pattern}' in output.")
                text = re.sub(pattern, "[unverified observation - non-certified]", text, flags=re.IGNORECASE)

        # 1. Strip markdown fences if present
        json_str = text
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            json_str = fence_match.group(1).strip()
        else:
            # Try to extract the first outer {...} block
            brace_match = re.search(r"(\{[\s\S]*\})", text)
            if brace_match:
                json_str = brace_match.group(1).strip()

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse JSON from VLM output: {jde}. Raw snippet: {text[:200]}")
            raise VisionOutputValidationError(f"Malformed JSON from vision model: {jde}") from jde

        if not isinstance(parsed, dict):
            raise VisionOutputValidationError("Vision model output must be a JSON object.")

        observations = parsed.get("observation", [])
        interpretations = parsed.get("interpretation", [])
        uncertainties = parsed.get("uncertainty", [])

        # Normalize string items if model returned a single string instead of list
        if isinstance(observations, str):
            observations = [observations] if observations.strip() else []
        if isinstance(interpretations, str):
            interpretations = [interpretations] if interpretations.strip() else []
        if isinstance(uncertainties, str):
            uncertainties = [uncertainties] if uncertainties.strip() else []

        if not isinstance(observations, list):
            raise VisionOutputValidationError("'observation' field must be a list.")
        if not isinstance(interpretations, list):
            raise VisionOutputValidationError("'interpretation' field must be a list.")
        if not isinstance(uncertainties, list):
            raise VisionOutputValidationError("'uncertainty' field must be a list.")

        # Ensure observation is non-empty (TRD ?18.1, Test Plan)
        cleaned_obs = [str(o).strip() for o in observations if str(o).strip()]
        if not cleaned_obs:
            raise VisionOutputValidationError("'observation' list must not be empty.")

        cleaned_interp = [str(i).strip() for i in interpretations if str(i).strip()]
        cleaned_uncert = [str(u).strip() for u in uncertainties if str(u).strip()]

        # Ensure uncertainty has at least standard disclaimer hedge if empty
        if not cleaned_uncert:
            cleaned_uncert = ["AI analysis only ? not a certified inspection verdict or statutory guarantee."]

        return VisionResult(
            observation=cleaned_obs,
            interpretation=cleaned_interp,
            uncertainty=cleaned_uncert,
            model_used=model_used,
        )

    def analyze(
        self,
        image_path: Path,
        prompt: Optional[str] = None,
        model_id: str = "local-vision-model",
        model_path: Optional[str] = None,
        on_retry: Optional[Callable[[int, int, str], None]] = None,
    ) -> VisionResult:
        """Execute multimodal vision analysis on an image file."""
        b64_image = self.encode_image(image_path)
        effective_prompt = prompt or "Inspect this equipment image and detail all visible conditions and anomalies."

        target_model = model_path or model_id

        # 1. Health check: check if Ollama is reachable and model is available locally
        if hasattr(self._provider, "check_model_health"):
            health = self._provider.check_model_health(target_model)
            if not health.get("available", False):
                msg = health.get("message", f"Local vision model unavailable: {target_model}")
                logger.error(f"[model_health] {msg}")
                raise VisionModelUnavailableError(msg)
        elif hasattr(self._provider, "is_provider_available"):
            if not self._provider.is_provider_available():
                msg = f"Local Ollama provider is unreachable. Please ensure Ollama is running."
                logger.error(f"[model_health] {msg}")
                raise VisionModelUnavailableError(msg)
            if hasattr(self._provider, "is_model_available") and not self._provider.is_model_available(target_model):
                msg = f"Local vision model unavailable: {target_model}. Run: ollama pull {target_model}"
                logger.error(f"[model_health] {msg}")
                raise VisionModelUnavailableError(msg)

        logger.info(
            f"[VLM_INFERENCE_START] Model: '{target_model}', Image: '{image_path.name}' "
            f"({image_path.stat().st_size} bytes, b64_len={len(b64_image)})"
        )

        try:
            # Check if generate supports retry/timeout kwargs
            try:
                raw_response = self._provider.generate(
                    model_id=target_model,
                    prompt=effective_prompt,
                    images=[b64_image],
                    system=VISION_SYSTEM_PROMPT,
                    format="json",
                    timeout=settings.ollama.vision_timeout_s,
                    max_retries=settings.ollama.max_retries,
                    on_retry=on_retry,
                )
            except TypeError:
                # Fallback for mock providers that don't accept extra kwargs
                raw_response = self._provider.generate(
                    model_id=target_model,
                    prompt=effective_prompt,
                    images=[b64_image],
                    system=VISION_SYSTEM_PROMPT,
                    format="json",
                )
            logger.info(f"[VLM_INFERENCE_RESPONSE] Raw Response: {raw_response[:300]}")
        except ModelInferenceTimeoutError as e:
            logger.error(f"[model_health] Local VLM '{target_model}' timed out after retries: {e}")
            raise VisionTimeoutError(f"Local vision model timed out: {e}") from e
        except (ModelUnavailable, ProviderUnavailable) as e:
            logger.error(f"[model_health] Local VLM '{target_model}' is unavailable: {e}")
            raise VisionModelUnavailableError(f"Local vision model unavailable: {e}") from e
        except Exception as e:
            if isinstance(e, VisionServiceError):
                raise
            logger.error(f"Error during VLM inference: {e}", exc_info=True)
            raise VisionServiceError(f"Vision inference error: {e}") from e

        return self.parse_and_validate_output(raw_response, model_used=model_id)


_vision_service_instance: Optional[VisionService] = None


def get_vision_service(provider: Optional[ModelProvider] = None) -> VisionService:
    global _vision_service_instance
    if _vision_service_instance is None or provider is not None:
        _vision_service_instance = VisionService(provider=provider)
    return _vision_service_instance
