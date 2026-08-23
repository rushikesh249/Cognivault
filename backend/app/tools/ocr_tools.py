"""OCR Extraction Tool (TRD Section 12, Table 31, Component #12)."""

import logging
from pathlib import Path
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.multimodal.ocr_service import get_ocr_service
from backend.app.persistence.db import get_db_context
from backend.app.persistence.file_repository import FileRepository
from backend.app.tools.base import BaseTool, ToolContext, ToolError, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.ocr")


class ExtractTextInput(BaseModel):
    file_id: str = Field(..., min_length=1, description="Uploaded document file identifier or relative path")
    page: int = Field(default=1, ge=1, description="1-indexed document page number")


class ExtractTextOutput(BaseModel):
    text: str = Field(..., description="Extracted text from scanned page")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Average OCR confidence score")


class ExtractTextFromScanTool(BaseTool):
    """Tool for OCR extraction from scanned pages (TRD Table 31)."""

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
        logger.info(f"Executing OCR extraction for file '{input_data.file_id}' (p.{input_data.page})")
        
        # 1. Resolve file path from database or uploads directory
        target_path: Path
        with get_db_context() as session:
            repo = FileRepository(session)
            file_record = repo.get_by_id(input_data.file_id)
            if file_record:
                target_path = Path(file_record.storage_path)
            else:
                # Check directly in uploads or demo_inputs directory
                direct_upload = settings.paths.uploads_dir / input_data.file_id
                demo_path = Path("knowledge_base/demo_inputs") / input_data.file_id
                if direct_upload.exists():
                    target_path = direct_upload
                elif demo_path.exists():
                    target_path = demo_path
                else:
                    raise ToolError(f"Target document '{input_data.file_id}' not found in file registry or storage.")

        if not target_path.exists():
            raise ToolError(f"Document file '{target_path}' missing from disk.")

        ocr_svc = get_ocr_service()
        try:
            doc_result = ocr_svc.extract(target_path)
            # Find requested page (1-indexed)
            if input_data.page <= len(doc_result.pages):
                page_res = doc_result.pages[input_data.page - 1]
                return ExtractTextOutput(
                    text=page_res.extracted_text,
                    confidence=page_res.ocr_confidence,
                )
            else:
                return ExtractTextOutput(
                    text=doc_result.full_text,
                    confidence=0.90,
                )
        except Exception as e:
            logger.error(f"OCR execution failed on '{target_path}': {e}", exc_info=True)
            raise ToolError(f"OCR extraction failed: {e}") from e
