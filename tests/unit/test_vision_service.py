"""Unit tests for Vision Service & VisionResult schema (TRD ?18, ?18.1, PRD ?13, Test Plan P18)."""

import io
import json
import pytest
from pathlib import Path
from PIL import Image

from backend.app.models.exceptions import ModelUnavailable, ProviderUnavailable
from backend.app.models.provider import ModelProvider
from backend.app.models.schema import ModelConfig, ModelStatus, ProviderStatus
from backend.app.multimodal.vision_service import (
    VisionInvalidImageError,
    VisionModelUnavailableError,
    VisionOutputValidationError,
    VisionResult,
    VisionService,
    get_vision_service,
)


class MockVisionProvider(ModelProvider):
    """Mock provider returning configurable VLM responses."""

    def __init__(self, response: str = "", available: bool = True):
        self.response = response
        self.available = available
        self.generate_calls = []

    def is_provider_available(self) -> bool:
        return self.available

    def is_model_available(self, model_identifier: str) -> bool:
        return self.available

    def get_provider_status(self) -> ProviderStatus:
        return ProviderStatus.AVAILABLE if self.available else ProviderStatus.UNAVAILABLE

    def get_model_status(self, model_config: ModelConfig) -> ModelStatus:
        return ModelStatus.AVAILABLE if self.available else ModelStatus.UNAVAILABLE

    def list_available_models(self):
        return ["llava:7b-v1.5-q4_K_M"] if self.available else []

    def check_model_health(self, model_identifier: str = "local-vision-model") -> dict:
        if not self.available:
            return {"available": False, "provider_online": False, "model_found": False, "message": "Mock provider unavailable"}
        return {"available": True, "provider_online": True, "model_found": True, "message": "Model available"}

    def ensure_loaded(self, model_id: str) -> bool:
        return True

    def unload(self, model_id: str) -> bool:
        return True

    def unload_lru(self) -> bool:
        return True

    def generate(self, model_id: str, prompt: str, images=None, system=None, format=None, stream=False) -> str:
        if not self.available:
            raise ProviderUnavailable("Mock provider unavailable")
        self.generate_calls.append({"model_id": model_id, "prompt": prompt, "images": images})
        return self.response


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    img_path = tmp_path / "sample_weld.jpg"
    img = Image.new("RGB", (100, 100), color=(128, 64, 32))
    img.save(img_path, format="JPEG")
    return img_path


def test_vision_service_initialization_and_singleton():
    """Verify VisionService singleton and initialization."""
    svc1 = get_vision_service()
    assert svc1 is not None
    assert isinstance(svc1, VisionService)


def test_vision_service_image_encoding(sample_image: Path):
    """Verify image to Base64 encoding roundtrip."""
    svc = VisionService(provider=MockVisionProvider())
    b64_str = svc.encode_image(sample_image)
    assert isinstance(b64_str, str)
    assert len(b64_str) > 0


def test_vision_service_missing_image_file_raises_invalid_image(tmp_path: Path):
    """Verify VisionInvalidImageError on non-existent file."""
    svc = VisionService(provider=MockVisionProvider())
    missing_path = tmp_path / "non_existent.jpg"
    with pytest.raises(VisionInvalidImageError):
        svc.encode_image(missing_path)


def test_vision_result_schema_parsing_valid_json(sample_image: Path):
    """Verify parsing valid VLM JSON response into VisionResult."""
    valid_json = json.dumps({
        "observation": ["Flange bolt head shows rust pitting", "Weld bead has irregular discoloration"],
        "interpretation": ["Likely atmospheric moisture exposure", "Potential localized corrosion"],
        "uncertainty": ["Lighting angle limits depth assessment"],
    })
    provider = MockVisionProvider(response=valid_json)
    svc = VisionService(provider=provider)

    result = svc.analyze(sample_image, model_id="local-vision-model")
    assert isinstance(result, VisionResult)
    assert len(result.observation) == 2
    assert "rust pitting" in result.observation[0]
    assert len(result.interpretation) == 2
    assert len(result.uncertainty) == 1
    assert result.model_used == "local-vision-model"


def test_vision_result_markdown_json_fence_stripping(sample_image: Path):
    """Verify parsing VLM output enclosed in markdown code fences."""
    markdown_output = """```json
{
  "observation": ["Discoloration near high-pressure valve fitting"],
  "interpretation": ["Possible minor thermal oxidation"],
  "uncertainty": ["Resolution insufficient to confirm wall thinning"]
}
```"""
    provider = MockVisionProvider(response=markdown_output)
    svc = VisionService(provider=provider)

    result = svc.analyze(sample_image, model_id="local-vision-model")
    assert isinstance(result, VisionResult)
    assert len(result.observation) == 1
    assert "Discoloration" in result.observation[0]
    assert result.model_used == "local-vision-model"


def test_vision_result_rejects_empty_observation(sample_image: Path):
    """Verify rejection when observation list is empty (TRD ?18.1 requirement)."""
    empty_obs_json = json.dumps({
        "observation": [],
        "interpretation": ["Some interpretation"],
        "uncertainty": ["Some uncertainty"],
    })
    provider = MockVisionProvider(response=empty_obs_json)
    svc = VisionService(provider=provider)

    with pytest.raises(VisionOutputValidationError):
        svc.analyze(sample_image, model_id="local-vision-model")


def test_vision_service_sanitizes_certified_inspection_verdict(sample_image: Path):
    """Verify forbidden certified engineering verdict phrases are redacted/sanitized (TRD ?18)."""
    prohibited_json = json.dumps({
        "observation": ["Crack detected; certified inspection verdict confirms replacement needed."],
        "interpretation": ["Certified engineering diagnosis indicates fatigue failure."],
        "uncertainty": ["None"],
    })
    provider = MockVisionProvider(response=prohibited_json)
    svc = VisionService(provider=provider)

    result = svc.analyze(sample_image, model_id="local-vision-model")
    # Verify the phrase "certified inspection verdict" was sanitized
    combined_obs = " ".join(result.observation)
    assert "certified inspection verdict" not in combined_obs.lower()


def test_vision_service_handles_model_unavailable(sample_image: Path):
    """Verify VisionModelUnavailableError when VLM provider is unreachable."""
    provider = MockVisionProvider(available=False)
    svc = VisionService(provider=provider)

    with pytest.raises(VisionModelUnavailableError):
        svc.analyze(sample_image, model_id="local-vision-model")
