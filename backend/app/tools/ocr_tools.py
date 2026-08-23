"""OCR Extraction Tool Contract (TRD Section 12, Table 31, Component #12).

Phase 5 typed contract and schema. Real PaddleOCR local service arrives in Phase 8.
"""

import logging
from pydantic import BaseModel, Field

from backend.app.tools.base import BaseTool, ToolContext, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.ocr")


class ExtractTextInput(BaseModel):
    file_id: str = Field(..., min_length=1, description="Uploaded document file identifier")
    page: int = Field(default=1, ge=1, description="1-indexed document page number")


class ExtractTextOutput(BaseModel):
    text: str = Field(..., description="Extracted text from scanned page")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Average OCR confidence score")


class ExtractTextFromScanTool(BaseTool):
    """Tool contract for OCR extraction from scanned pages (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="extract_text_from_scan",
            purpose="OCR a page image.",
            input_schema=ExtractTextInput,
            output_schema=ExtractTextOutput,
            allowed_task_types=["document"],
            timeout_s=15.0,
            fs_boundary="local model only",
            network="none",
        )

    def execute(self, input_data: ExtractTextInput, ctx: ToolContext) -> ExtractTextOutput:
        logger.info(f"extract_text_from_scan contract called for file '{input_data.file_id}' (p.{input_data.page})")
        return ExtractTextOutput(
            text="[Phase 5 Typed Stub: Local PaddleOCR extraction deferred to Phase 8]",
            confidence=1.0,
        )
