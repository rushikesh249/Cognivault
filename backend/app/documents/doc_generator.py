"""Document Generation Engine (TRD Section 22, ADR-007, Component #17)."""

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.app.core.config import settings
from backend.app.documents.templates.approval_note import render_approval_note
from backend.app.documents.templates.pdf_report import render_pdf_report
from backend.app.documents.templates.presentation_deck import render_presentation_deck
from backend.app.documents.templates.spreadsheet_report import render_spreadsheet_report

logger = logging.getLogger("sovereign_workbench.documents.generator")

SUPPORTED_FORMATS = ("docx", "xlsx", "pptx", "pdf")


class DocumentGenerationError(Exception):
    """Raised when document generation or template rendering fails."""
    pass


class DocGenerator:
    """
    Document Generation engine orchestrating multi-format artifact creation (TRD Section 22).
    Supports DOCX (Approval Note), XLSX (Spreadsheet), PPTX (Slide Deck), and PDF (Technical Report).
    """

    def __init__(self, outputs_dir: Optional[Path] = None):
        self.outputs_dir = outputs_dir or (settings.paths.data_dir / "outputs")
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        kind: str,
        data: Dict[str, Any],
        artifact_id: Optional[str] = None,
    ) -> Tuple[Path, str]:
        """
        Render deliverable artifact from structured data payload (TRD Section 22).
        Returns (output_path, artifact_id).
        """
        normalized_kind = (kind or "").strip().lower()
        if normalized_kind not in SUPPORTED_FORMATS:
            raise DocumentGenerationError(
                f"Unsupported document kind '{kind}'. Supported formats: {', '.join(SUPPORTED_FORMATS)}."
            )

        # Basic schema validation
        if not isinstance(data, dict):
            raise DocumentGenerationError("Document generation payload must be a JSON dictionary.")

        art_id = artifact_id or str(uuid.uuid4())
        filename = f"{art_id}.{normalized_kind}"
        target_path = (self.outputs_dir / filename).resolve()

        # Enforce canonical path containment inside data/outputs
        canon_out_dir = self.outputs_dir.resolve()
        if not target_path.is_relative_to(canon_out_dir):
            raise DocumentGenerationError(f"Security: Target path '{target_path}' escapes outputs directory.")

        try:
            if normalized_kind == "docx":
                render_approval_note(data, target_path)
            elif normalized_kind == "xlsx":
                render_spreadsheet_report(data, target_path)
            elif normalized_kind == "pptx":
                render_presentation_deck(data, target_path)
            elif normalized_kind == "pdf":
                render_pdf_report(data, target_path)

            logger.info(f"Successfully generated {normalized_kind.upper()} artifact: {target_path} (id: {art_id})")
            return target_path, art_id
        except DocumentGenerationError:
            raise
        except Exception as e:
            logger.error(f"Failed rendering {normalized_kind.upper()} artifact: {e}", exc_info=True)
            raise DocumentGenerationError(f"Failed rendering {normalized_kind.upper()} artifact: {e}") from e


_doc_generator_instance: Optional[DocGenerator] = None


def get_doc_generator() -> DocGenerator:
    global _doc_generator_instance
    if _doc_generator_instance is None:
        _doc_generator_instance = DocGenerator()
    return _doc_generator_instance
