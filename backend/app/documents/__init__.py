"""Document Generation Package (TRD Section 22, Component #17)."""

from backend.app.documents.doc_generator import (
    DocGenerator,
    DocumentGenerationError,
    get_doc_generator,
)

__all__ = [
    "DocGenerator",
    "DocumentGenerationError",
    "get_doc_generator",
]
