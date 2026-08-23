"""Unit tests for Document Generator and Approval Note Template (TRD Section 22, PRD Requirement #8)."""

from pathlib import Path
import docx
import pytest

from backend.app.documents.doc_generator import DocGenerator, DocumentGenerationError


def test_doc_generator_approval_note_rendering(tmp_path):
    """Verify DOCX Approval Note renders all 7 mandatory sections and opens in python-docx."""
    generator = DocGenerator(outputs_dir=tmp_path)
    
    payload = {
        "task_id": "test-task-12345",
        "title": "TECHNICAL APPROVAL NOTE: EQUIPMENT COMPLIANCE",
        "facility": "Primary Refining Unit 02",
        "summary": "Full compliance evaluation executed.",
        "critical_findings": [
            "Flange FL-102B wall thinning (1.65mm).",
            "PRV-204 calibration overdue by 2 months."
        ],
        "compliance_gaps": [
            ("Flange thinning", "Safety SOP - Section 4.2 (p.12)", "CRITICAL NON-COMPLIANCE"),
            ("PRV overdue", "Equipment Standards - Section 11.4 (p.56)", "MAJOR GAP"),
        ],
        "recommendations": [
            "Schedule immediate bolt replacement.",
            "Recertify PRV-204 within 48 hours."
        ],
        "citations": [
            "Safety SOP - Section 4.2 (p.12)",
            "Equipment Standards - Section 11.4 (p.56)",
        ],
    }

    output_path, art_id = generator.render(kind="docx", data=payload)
    assert output_path.exists()
    assert art_id is not None

    # Verify document opens cleanly in python-docx
    doc = docx.Document(str(output_path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    
    # 1. Title block
    assert "APPROVAL NOTE" in full_text.upper()
    # 2. Inspection summary
    assert "Inspection Overview" in full_text
    # 3. Critical findings
    assert "Critical Inspection Findings" in full_text
    # 4. Compliance gaps & SOP citations
    assert "Compliance Gaps" in full_text
    # 5. Actionable recommendations
    assert "Actionable Engineering Recommendations" in full_text
    # 6. AI disclaimer footer
    footer_text = "\n".join(p.text for s in doc.sections for p in s.footer.paragraphs)
    assert "AI-Generated Draft" in footer_text


def test_doc_generator_unsupported_kind_rejection(tmp_path):
    """Verify non-docx formats are rejected in Phase 8 (strictly DOCX)."""
    generator = DocGenerator(outputs_dir=tmp_path)
    with pytest.raises(DocumentGenerationError, match="Unsupported document kind"):
        generator.render(kind="xlsx", data={})


def test_doc_generator_invalid_payload_rejection(tmp_path):
    """Verify non-dictionary payload raises DocumentGenerationError."""
    generator = DocGenerator(outputs_dir=tmp_path)
    with pytest.raises(DocumentGenerationError):
        generator.render(kind="docx", data="invalid-payload")  # type: ignore
