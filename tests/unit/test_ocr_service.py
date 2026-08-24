"""Unit tests for Local OCR Service (TRD Section 17, Tables 39 & 40, ADR-007)."""

from pathlib import Path
import cv2
import numpy as np
import pytest

from backend.app.multimodal.ocr_service import OCRService, get_ocr_service


def test_ocr_service_initialization_and_singleton():
    """Verify OCR service instance configuration."""
    svc = get_ocr_service()
    assert svc.dpi == 300
    assert svc.confidence_threshold == 0.6


def test_opencv_preprocessing_and_deskew():
    """Verify OpenCV deskew and denoise pipeline."""
    svc = OCRService(dpi=300, confidence_threshold=0.6)
    
    # Create synthetic test image (white canvas with dark rectangle)
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "SOVEREIGN OCR TEST", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    preprocessed, status = svc.preprocess_image(img)
    assert isinstance(preprocessed, np.ndarray)
    assert status in ["ocr_clean", "ocr_deskewed"]


def test_native_vs_scanned_page_detection():
    """Verify PyMuPDF native text detection on synthetic report PDF."""
    svc = get_ocr_service()
    pdf_path = Path("knowledge_base/demo_inputs/scanned_inspection_report.pdf")
    
    if not pdf_path.exists():
        pytest.skip("scanned_inspection_report.pdf not found")

    result = svc.extract_from_pdf(pdf_path, force_ocr=False)
    assert result.total_pages >= 2
    assert result.native_pages >= 1
    assert len(result.pages) == result.total_pages
    assert "CORROSION" in result.full_text.upper() or "INSPECTION" in result.full_text.upper()


def test_low_confidence_flagging():
    """Verify pages with confidence < 0.6 are flagged with low_confidence=True."""
    svc = OCRService(confidence_threshold=0.8) # High threshold to test flagging
    pdf_path = Path("knowledge_base/demo_inputs/scanned_inspection_report.pdf")
    
    if not pdf_path.exists():
        pytest.skip("scanned_inspection_report.pdf not found")

    result = svc.extract_from_pdf(pdf_path, force_ocr=True)
    assert isinstance(result.has_low_confidence_pages, bool)
    for p in result.pages:
        if p.ocr_confidence < 0.8:
            assert p.low_confidence is True
            assert p.preprocessing_status == "ocr_low_confidence"
