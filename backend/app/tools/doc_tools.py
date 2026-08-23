"""Document Generation Tool Contracts (TRD Section 12, Table 31).

Phase 5 typed contracts and schemas. Real artifact generators arrive in Phase 8/12.
"""

from typing import Any, Dict
import logging
import uuid
from pydantic import BaseModel, Field

from backend.app.tools.base import BaseTool, ToolContext, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.doc")


class DocGenInput(BaseModel):
    template: str = Field(..., min_length=1, description="Template identifier or format name")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured document data")


class DocGenOutput(BaseModel):
    artifact_id: str = Field(..., description="Unique artifact identifier for generated file")


class CreateDocxTool(BaseTool):
    """Tool contract for generating DOCX approval notes and reports (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_docx",
            purpose="Generate an Approval Note or report DOCX.",
            input_schema=DocGenInput,
            output_schema=DocGenOutput,
            allowed_task_types=["document"],
            timeout_s=20.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        art_id = str(uuid.uuid4())
        logger.info(f"create_docx contract called for task '{ctx.task_id}' (template: {input_data.template})")
        return DocGenOutput(artifact_id=art_id)


class CreateXlsxTool(BaseTool):
    """Tool contract for generating analysis spreadsheets (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_xlsx",
            purpose="Generate an analysis spreadsheet.",
            input_schema=DocGenInput,
            output_schema=DocGenOutput,
            allowed_task_types=["document"],
            timeout_s=20.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        art_id = str(uuid.uuid4())
        logger.info(f"create_xlsx contract called for task '{ctx.task_id}' (template: {input_data.template})")
        return DocGenOutput(artifact_id=art_id)


class CreatePptxTool(BaseTool):
    """Tool contract for generating management summary decks (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_pptx",
            purpose="Generate a management summary deck.",
            input_schema=DocGenInput,
            output_schema=DocGenOutput,
            allowed_task_types=["document"],
            timeout_s=20.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        art_id = str(uuid.uuid4())
        logger.info(f"create_pptx contract called for task '{ctx.task_id}' (template: {input_data.template})")
        return DocGenOutput(artifact_id=art_id)


class CreatePdfTool(BaseTool):
    """Tool contract for generating PDF reports (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_pdf",
            purpose="Generate a PDF report.",
            input_schema=DocGenInput,
            output_schema=DocGenOutput,
            allowed_task_types=["document"],
            timeout_s=20.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        art_id = str(uuid.uuid4())
        logger.info(f"create_pdf contract called for task '{ctx.task_id}' (template: {input_data.template})")
        return DocGenOutput(artifact_id=art_id)
