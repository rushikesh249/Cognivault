"""Document Generation Tools for Sovereign Agentic Workbench (TRD Section 12, Table 31, Section 22)."""

import logging
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.documents.doc_generator import DocumentGenerationError, get_doc_generator
from backend.app.persistence.artifact_repository import ArtifactRepository
from backend.app.persistence.db import get_db_context
from backend.app.tools.base import BaseTool, ToolContext, ToolError, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.doc")


class DocGenInput(BaseModel):
    """Input payload schema for document creation tools (TRD Table 31)."""
    template: str = Field(..., min_length=1, description="Template identifier or format name")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured document data")


class DocGenOutput(BaseModel):
    """Output schema for document creation tools returning the created artifact_id (TRD Table 31)."""
    artifact_id: str = Field(..., description="Unique UUID identifier of the generated deliverable artifact.")


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
            timeout_s=30.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        logger.info(f"Executing create_docx for task '{ctx.task_id}' (template: {input_data.template})")
        doc_gen = get_doc_generator()
        task_id = ctx.task_id

        payload = dict(input_data.data)
        payload.setdefault("task_id", task_id)

        try:
            output_path, artifact_id = doc_gen.render(
                kind="docx",
                data=payload,
            )

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
    """Tool for generating technical inspection spreadsheets in XLSX format (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_xlsx",
            purpose="Generate a technical inspection summary in XLSX spreadsheet format.",
            input_schema=DocGenInput,
            output_schema=DocGenOutput,
            allowed_task_types=["document"],
            timeout_s=30.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        logger.info(f"Executing create_xlsx for task '{ctx.task_id}' (template: {input_data.template})")
        doc_gen = get_doc_generator()
        task_id = ctx.task_id

        payload = dict(input_data.data)
        payload.setdefault("task_id", task_id)

        try:
            output_path, artifact_id = doc_gen.render(
                kind="xlsx",
                data=payload,
            )

            sources = payload.get("citations", [])
            title = payload.get("title", "Technical Inspection & Compliance Summary Spreadsheet")

            with get_db_context() as session:
                repo = ArtifactRepository(session)
                repo.create(
                    task_id=task_id,
                    kind="xlsx",
                    title=title,
                    storage_path=str(output_path),
                    sources=sources,
                    artifact_id=artifact_id,
                )

            return DocGenOutput(artifact_id=artifact_id)
        except DocumentGenerationError as dge:
            raise ToolError(str(dge)) from dge
        except Exception as e:
            logger.error(f"create_xlsx failed for task '{task_id}': {e}", exc_info=True)
            raise ToolError(f"Failed to generate XLSX document: {e}") from e


class CreatePptxTool(BaseTool):
    """Tool for generating management summary decks in PPTX format (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_pptx",
            purpose="Generate a management summary presentation deck in PPTX format.",
            input_schema=DocGenInput,
            output_schema=DocGenOutput,
            allowed_task_types=["document"],
            timeout_s=30.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        logger.info(f"Executing create_pptx for task '{ctx.task_id}' (template: {input_data.template})")
        doc_gen = get_doc_generator()
        task_id = ctx.task_id

        payload = dict(input_data.data)
        payload.setdefault("task_id", task_id)

        try:
            output_path, artifact_id = doc_gen.render(
                kind="pptx",
                data=payload,
            )

            sources = payload.get("citations", [])
            title = payload.get("title", "Executive Management Inspection & Compliance Presentation Deck")

            with get_db_context() as session:
                repo = ArtifactRepository(session)
                repo.create(
                    task_id=task_id,
                    kind="pptx",
                    title=title,
                    storage_path=str(output_path),
                    sources=sources,
                    artifact_id=artifact_id,
                )

            return DocGenOutput(artifact_id=artifact_id)
        except DocumentGenerationError as dge:
            raise ToolError(str(dge)) from dge
        except Exception as e:
            logger.error(f"create_pptx failed for task '{task_id}': {e}", exc_info=True)
            raise ToolError(f"Failed to generate PPTX document: {e}") from e


class CreatePdfTool(BaseTool):
    """Tool for generating technical inspection reports in PDF format (TRD Table 31)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_pdf",
            purpose="Generate a formal technical inspection report in PDF format.",
            input_schema=DocGenInput,
            output_schema=DocGenOutput,
            allowed_task_types=["document"],
            timeout_s=30.0,
            fs_boundary="writes to data/outputs/ only",
            network="none",
        )

    def execute(self, input_data: DocGenInput, ctx: ToolContext) -> DocGenOutput:
        logger.info(f"Executing create_pdf for task '{ctx.task_id}' (template: {input_data.template})")
        doc_gen = get_doc_generator()
        task_id = ctx.task_id

        payload = dict(input_data.data)
        payload.setdefault("task_id", task_id)

        try:
            output_path, artifact_id = doc_gen.render(
                kind="pdf",
                data=payload,
            )

            sources = payload.get("citations", [])
            title = payload.get("title", "Technical Inspection & Compliance Report (PDF)")

            with get_db_context() as session:
                repo = ArtifactRepository(session)
                repo.create(
                    task_id=task_id,
                    kind="pdf",
                    title=title,
                    storage_path=str(output_path),
                    sources=sources,
                    artifact_id=artifact_id,
                )

            return DocGenOutput(artifact_id=artifact_id)
        except DocumentGenerationError as dge:
            raise ToolError(str(dge)) from dge
        except Exception as e:
            logger.error(f"create_pdf failed for task '{task_id}': {e}", exc_info=True)
            raise ToolError(f"Failed to generate PDF document: {e}") from e
