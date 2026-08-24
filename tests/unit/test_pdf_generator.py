"""Unit tests for PDF Technical Report Generator (TRD Section 22, Component #17)."""

from pathlib import Path
import fitz  # PyMuPDF
import pytest

from backend.app.documents.templates.pdf_report import render_pdf_report


@pytest.fixture
def sample_pdf_data():
    return {
        "title": "TECHNICAL INSPECTION & COMPLIANCE EVALUATION REPORT",
        "task_id": "TASK-PDF-TEST-01",
        "facility": "Offshore Platform Alpha - Gas Compression Train",
        "timestamp": "2026-08-24 18:00 UTC",
        "status": "ACTION REQUIRED — NON-COMPLIANCE DETECTED",
        "summary": "Autonomous document intelligence analysis executed on offshore gas compression maintenance logs and safety procedures.",
        "critical_findings": [
            "First stage scrubber level transmitter LT-101 drifting by 8.5%.",
            "Compressor suction bottle bolt torque below specified engineering threshold.",
            "Emergency depressurization ESD valve stroke time exceeded 10-second requirement.",
        ],
        "compliance_gaps": [
            ("Level Transmitter Drift", "Offshore Instrument Standards ISA-5.1", "MAJOR GAP"),
            ("Bolt Torque Inadequacy", "Mechanical Bolting Standard ASME PCC-1", "CRITICAL NON-COMPLIANCE"),
            ("ESD Stroke Time Exceeded", "Emergency Shutdown SOP Section 6.3", "CRITICAL NON-COMPLIANCE"),
        ],
        "recommendations": [
            "Recalibrate LT-101 and conduct loop check immediately.",
            "Re-torque all suction bottle flange studs to 450 ft-lbs.",
            "Overhaul ESD actuator pilot valve to restore sub-10s stroke speed.",
        ],
    }


def test_pdf_generation_success(sample_pdf_data, tmp_path):
    """Verify PDF technical report renders successfully with styled flowables and table."""
    output_path = tmp_path / "report.pdf"
    res = render_pdf_report(sample_pdf_data, output_path)

    assert res.exists()
    assert res.stat().st_size > 2000

    # Parse with PyMuPDF
    doc = fitz.open(str(output_path))
    assert len(doc) >= 1

    full_text = "\n".join(page.get_text() for page in doc)
    assert "TECHNICAL INSPECTION" in full_text
    assert "TASK-PDF-TEST-01" in full_text
    assert "Inspection Overview & Summary" in full_text
    assert "Critical Inspection Findings" in full_text
    assert "Compliance Gaps" in full_text
    assert "Actionable Engineering Recommendations" in full_text
    assert "Prepared Autonomously By" in full_text
    assert "Reviewed & Endorsed By" in full_text

    doc.close()


def test_pdf_running_footer_disclaimer(sample_pdf_data, tmp_path):
    """Verify running footer contains mandatory non-certified draft disclaimer and page numbering."""
    output_path = tmp_path / "report_footer.pdf"
    render_pdf_report(sample_pdf_data, output_path)

    doc = fitz.open(str(output_path))
    for idx, page in enumerate(doc):
        page_text = page.get_text()
        assert "AI-Generated Draft" in page_text, f"Missing footer disclaimer on page {idx+1}"
        assert "Non-Certified Verdict" in page_text, f"Missing non-certified notice on page {idx+1}"
        assert f"Page {idx+1}" in page_text, f"Missing page number on page {idx+1}"
    doc.close()
