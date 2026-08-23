"""Document Generation Engine (TRD Section 22, ADR-007, Component #17)."""

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.app.core.config import settings
from backend.app.documents.templates.approval_note import render_approval_note

logger = logging.getLogger("sovereign_workbench.documents.generator")


class DocumentGenerationError(Exception):
    """Raised when document generation or template rendering fails."""
    pass


class DocGenerator:
    """
    Document Generation engine orchestrating artifact creation (TRD Section 22).
    Phase 8 implements DOCX Approval Note generator.
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
        if kind != "docx":
            raise DocumentGenerationError(
                f"Unsupported document kind '{kind}' in Phase 8 (DOCX Approval Note supported exclusively)."
            )

        # Basic schema validation
        if not isinstance(data, dict):
            raise DocumentGenerationError("Document generation payload must be a JSON dictionary.")

        art_id = artifact_id or str(uuid.uuid4())
        filename = f"{art_id}.docx"
        target_path = (self.outputs_dir / filename).resolve()

        # Enforce canonical path containment inside data/outputs
        canon_out_dir = self.outputs_dir.resolve()
        if not target_path.is_relative_to(canon_out_dir):
            raise DocumentGenerationError(f"Security: Target path '{target_path}' escapes outputs directory.")

        try:
            render_approval_note(data, target_path)
            logger.info(f"Successfully generated DOCX artifact: {target_path} (id: {art_id})")
            return target_path, art_id
        except Exception as e:
            logger.error(f"Failed rendering DOCX artifact: {e}", exc_info=True)
            raise DocumentGenerationError(f"Failed rendering DOCX artifact: {e}") from e


_doc_generator_instance: Optional[DocGenerator] = None


def get_doc_generator() -> DocGenerator:
    global _doc_generator_instance
    if _doc_generator_instance is None:
        _doc_generator_instance = DocGenerator()
    return _doc_generator_instance
