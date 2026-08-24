"""Unit tests for Document Generation Engine (TRD Section 22, Component #17)."""

from pathlib import Path
import openpyxl
import pptx
import fitz
import docx
import pytest

from backend.app.documents.doc_generator import DocGenerator, DocumentGenerationError


@pytest.fixture
def doc_gen(tmp_path):
    return DocGenerator(outputs_dir=tmp_path)


@pytest.fixture
def sample_payload():
    return {
        "title": "INTEGRATED MULTI-FORMAT TEST REPORT",
        "task_id": "TASK-MULTI-01",
        "facility": "Primary Test Unit",
        "summary": "Multi-format generation verification.",
        "critical_findings": ["Finding A", "Finding B"],
        "compliance_gaps": [("Finding A", "SOP Clause 1", "MAJOR GAP")],
        "recommendations": ["Recommendation A", "Recommendation B"],
    }


def test_render_all_four_formats(doc_gen, sample_payload):
    """Verify DocGenerator renders all 4 supported formats (DOCX, XLSX, PPTX, PDF)."""
    formats = [
        ("docx", docx.Document),
        ("xlsx", lambda p: openpyxl.load_workbook(p, read_only=True)),
        ("pptx", pptx.Presentation),
        ("pdf", fitz.open),
    ]

    for kind, loader in formats:
        out_path, art_id = doc_gen.render(kind=kind, data=sample_payload)
        assert out_path.exists()
        assert out_path.suffix.lower() == f".{kind}"
        assert art_id in out_path.name

        # Verify loader opens file cleanly
        obj = loader(str(out_path))
        if hasattr(obj, "close"):
            obj.close()


def test_unsupported_kind_raises_error(doc_gen, sample_payload):
    """Verify unsupported document formats raise DocumentGenerationError."""
    unsupported = ["odt", "html", "rtf", "markdown", "csv"]
    for kind in unsupported:
        with pytest.raises(DocumentGenerationError) as exc_info:
            doc_gen.render(kind=kind, data=sample_payload)
        assert f"Unsupported document kind '{kind}'" in str(exc_info.value)


def test_invalid_payload_raises_error(doc_gen):
    """Verify non-dict payload raises DocumentGenerationError."""
    with pytest.raises(DocumentGenerationError):
        doc_gen.render(kind="docx", data="invalid string payload")


def test_path_escape_containment(tmp_path):
    """Verify output file is strictly contained within outputs_dir."""
    gen = DocGenerator(outputs_dir=tmp_path / "outputs")
    out_path, _ = gen.render(kind="pdf", data={"title": "Test"})
    assert out_path.is_relative_to((tmp_path / "outputs").resolve())
