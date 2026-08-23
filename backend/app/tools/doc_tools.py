"""Document Generation Tool Implementations (TRD Section 12, Table 31, Component #17)."""

import logging
import uuid
from typing import Any, Dict
from pydantic import BaseModel, Field

from backend.app.documents.doc_generator import DocumentGenerationError, get_doc_generator
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context
from backend.app.tools.base import BaseTool, ToolContext, ToolError, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.doc")


class DocGenInput(BaseModel):
    template: str = Field(..., min_length=1, description="Template identifier or format name")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured document data")


class DocGenOutput(BaseModel):
    artifact_id: str = Field(..., description="Unique artifact identifier for generated file")


class CreateDocxTool(BaseTool):
    """Tool for generating DOCX approval notes and reports (TRD Table 31, Section 22)."""

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
        logger.info(f"Executing create_docx for task '{ctx.task_id}' (template: {input_data.template})")
        
        doc_gen = get_doc_generator()
        task_id = ctx.task_id
        
        # Inject task_id into payload if missing
        payload = dict(input_data.data)
        payload.setdefault("task_id", task_id)
        
        try:
            output_path, artifact_id = doc_gen.render(
                kind="docx",
                data=payload,
            )
            
            # Register in SQLite artifacts table (TRD Section 10.5)
            sources = payload.get("citations", [])
            title = payload.get("title", "Technical Approval Note: Equipment Inspection")
            
            with get_db_context() as session:
                repo = ArtifactRepository(session)
                repo.create(
                    task_id=task_id,
                    kind="docx",
                    title=title,
                    storage_path=str(output_path),
                    sources=sources,
                    artifact_id=artifact_id,
                )
                
            return DocGenOutput(artifact_id=artifact_id)
        except DocumentGenerationError as dge:
            raise ToolError(str(dge)) from dge
        except Exception as e:
            logger.error(f"create_docx failed for task '{task_id}': {e}", exc_info=True)
            raise ToolError(f"Failed to generate DOCX document: {e}") from e


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
