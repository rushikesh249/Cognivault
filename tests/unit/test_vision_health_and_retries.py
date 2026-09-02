"""Tests for Vision health checks, timeout retries, routing safety, and unreadable OCR safeguards."""

from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from backend.app.models.exceptions import (
    ModelInferenceTimeoutError,
    ModelUnavailable,
    ProviderUnavailable,
)
from backend.app.multimodal.vision_service import (
    VisionModelUnavailableError,
    VisionService,
    VisionTimeoutError,
)
from backend.app.multimodal.ocr_service import OCRService
from backend.app.services.document_analysis import DocumentAnalysisService


class MockFailingProvider:
    def __init__(self, failure_mode="unavailable"):
        self.failure_mode = failure_mode
        self.retry_count = 0

    def check_model_health(self, model_identifier: str = "llava:7b-v1.5-q4_K_M"):
        if self.failure_mode == "provider_offline":
            return {"available": False, "provider_online": False, "model_found": False, "message": "Ollama provider unreachable"}
        elif self.failure_mode == "model_missing":
            return {"available": False, "provider_online": True, "model_found": False, "message": f"Model '{model_identifier}' not found in local Ollama"}
        return {"available": True, "provider_online": True, "model_found": True, "message": "Model available"}

    def generate(self, model_id, prompt, images=None, system=None, format=None, timeout=None, max_retries=2, on_retry=None):
        if self.failure_mode == "timeout":
            for r in range(1, max_retries + 1):
                self.retry_count += 1
                if on_retry:
                    on_retry(r, max_retries, f"Timed out (attempt {r}/{max_retries})")
            raise ModelInferenceTimeoutError(f"Inference timed out after {max_retries} attempts.")
        elif self.failure_mode == "unavailable":
            raise ModelUnavailable("Model not found in local storage.")
        return '{"observation": ["Valid flange weld"], "interpretation": ["Normal condition"], "uncertainty": ["None"]}'


def test_vision_health_check_provider_offline(tmp_path):
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # fake jpeg header

    provider = MockFailingProvider(failure_mode="provider_offline")
    service = VisionService(provider=provider)

    with pytest.raises(VisionModelUnavailableError) as exc_info:
        service.analyze(img_file, model_id="local-vision-model", model_path="llava:7b-v1.5-q4_K_M")
    assert "unavailable" in str(exc_info.value).lower() or "unreachable" in str(exc_info.value).lower()


def test_vision_health_check_model_missing(tmp_path):
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    provider = MockFailingProvider(failure_mode="model_missing")
    service = VisionService(provider=provider)

    with pytest.raises(VisionModelUnavailableError) as exc_info:
        service.analyze(img_file, model_id="local-vision-model", model_path="llava:7b-v1.5-q4_K_M")
    assert "not found" in str(exc_info.value).lower() or "unavailable" in str(exc_info.value).lower()


def test_vision_timeout_bounded_retries(tmp_path):
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    provider = MockFailingProvider(failure_mode="timeout")
    service = VisionService(provider=provider)

    retries_recorded = []
    def on_retry(idx, total, msg):
        retries_recorded.append((idx, total, msg))

    with pytest.raises(VisionTimeoutError) as exc_info:
        service.analyze(
            img_file,
            model_id="local-vision-model",
            model_path="llava:7b-v1.5-q4_K_M",
            on_retry=on_retry,
        )

    assert "timed out" in str(exc_info.value).lower()
    assert len(retries_recorded) == 2
    assert provider.retry_count == 2


def test_ocr_unreadable_produces_no_uuid_placeholder(tmp_path):
    """Verify that unreadable OCR produces explicit text instead of [Image Content: UUID]."""
    from PIL import Image
    blank_img = tmp_path / "blank.png"
    # Pure white blank image that produces 0 OCR text
    Image.new("RGB", (200, 200), color=(255, 255, 255)).save(blank_img)

    ocr = OCRService()
    result = ocr.extract_from_image(blank_img)

    assert "[Image Content:" not in result.full_text
    assert "No readable text was extracted from the supplied image." in result.full_text


def test_document_analysis_with_unreadable_text():
    """Verify document analysis does not hallucinate when input is unreadable text."""
    doc_service = DocumentAnalysisService()
    res = doc_service.analyze(
        extracted_text="No readable text was extracted from the supplied image.",
        goal="Extract findings and evaluate compliance",
        source_document="blank_scan.png",
    )

    assert res["summary"] == "No readable text was extracted from the supplied image."
    assert res["key_findings"] == []
    assert res["section_values"]["objectives"] == "Not found in the source document."
    assert res["grounding_verified"] is True
