"""Multimodal & OCR Services Package (TRD Section 17, ADR-007)."""

from backend.app.multimodal.ocr_service import (
    OCRDocumentResult,
    OCRPageResult,
    OCRService,
    get_ocr_service,
)

__all__ = [
    "OCRDocumentResult",
    "OCRPageResult",
    "OCRService",
    "get_ocr_service",
]
