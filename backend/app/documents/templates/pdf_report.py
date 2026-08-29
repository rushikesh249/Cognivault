"""PDF Technical Report Generator using ReportLab Platypus (TRD Section 22, Component #17)."""

import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand Colors
NAVY_COLOR = colors.HexColor("#102C57")
ICE_COLOR = colors.HexColor("#F0F4F8")
ALT_ROW_COLOR = colors.HexColor("#F9FBFC")
ALERT_COLOR = colors.HexColor("#B40000")
DARK_TEXT_COLOR = colors.HexColor("#212529")
MUTED_COLOR = colors.HexColor("#6C757D")
BORDER_COLOR = colors.HexColor("#D0D7DE")

DISCLAIMER_TEXT = "AI-Generated Draft — For Internal Engineering Review Only (Non-Certified Verdict)"


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render total page numbers and running disclaimer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_COLOR)

        # Running Top Header
        self.drawRightString(
            letter[0] - 0.75 * inch,
            letter[1] - 0.5 * inch,
            "CONFIDENTIAL / SOVEREIGN ON-PREMISE AI WORKBENCH",
        )
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(0.75 * inch, letter[1] - 0.55 * inch, letter[0] - 0.75 * inch, letter[1] - 0.55 * inch)

        # Running Footer Disclaimer & Page Number
        self.setFont("Helvetica-BoldOblique", 8)
        self.setFillColor(ALERT_COLOR)
        self.drawCentredString(letter[0] / 2.0, 0.5 * inch, DISCLAIMER_TEXT)

        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_COLOR)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, page_text)

        self.line(0.75 * inch, 0.65 * inch, letter[0] - 0.75 * inch, 0.65 * inch)
        self.restoreState()


def render_pdf_report(data: Dict[str, Any], output_path: Path) -> Path:
    """
    Render multi-page publication-quality PDF technical report using pure local ReportLab.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=NAVY_COLOR,
        spaceAfter=10,
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=NAVY_COLOR,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=DARK_TEXT_COLOR,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=4,
    )

    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=NAVY_COLOR,
    )

    meta_val_style = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=DARK_TEXT_COLOR,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white,
        alignment=1,  # Centered
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=DARK_TEXT_COLOR,
    )

    table_cell_alert = ParagraphStyle(
        "TableCellAlert",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
        textColor=ALERT_COLOR,
        alignment=1,
    )

    story = []

    # 1. Title Banner
    title_text = str(data.get("title", "TECHNICAL APPROVAL NOTE: EQUIPMENT INSPECTION COMPLIANCE"))
    story.append(Paragraph(title_text, title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY_COLOR, spaceBefore=2, spaceAfter=8))

    # 2. Metadata Box Table
    task_id = str(data.get("task_id", "TASK-AUTONOMOUS-01"))
    facility = str(data.get("facility", "Primary Refining Unit & Flare Header"))
    timestamp = str(data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))
    status_str = str(data.get("status", "ACTION REQUIRED — NON-COMPLIANCE DETECTED"))

    meta_table_data = [
        [Paragraph("Task ID / Ref:", meta_label_style), Paragraph(task_id, meta_val_style)],
        [Paragraph("Facility / Asset Unit:", meta_label_style), Paragraph(facility, meta_val_style)],
        [Paragraph("Evaluation Timestamp:", meta_label_style), Paragraph(timestamp, meta_val_style)],
        [
            Paragraph("Compliance Status:", meta_label_style),
            Paragraph(
                f"<font color='#B40000'><b>{status_str}</b></font>" if "ACTION REQUIRED" in status_str else status_str,
                meta_val_style,
            ),
        ],
    ]

    meta_table = Table(meta_table_data, colWidths=[2.2 * inch, 4.8 * inch])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), ICE_COLOR),
            ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FAFAFA")),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Section 1: Inspection Overview & Summary
    story.append(Paragraph("1. Inspection Overview & Summary", section_style))
    summary_text = str(data.get(
        "summary",
        "Autonomous document intelligence analysis was executed on the submitted inspection report. "
        "The document was processed through the Sovereign OCR engine and compared against the indexed standard "
        "operating procedures (SOPs), maintenance guidelines, and equipment compliance standards."
    ))
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 6))

    # 4. Section 2: Critical Findings
    story.append(Paragraph("2. Critical Inspection Findings", section_style))
    raw_findings = data.get("critical_findings", [
        "Corrosion fatigue detected on primary discharge flange bolts exceeding 1.5mm wall thinning threshold.",
        "Pressure relief valve PRV-204 calibration interval exceeded maximum allowable 12-month limit.",
        "Emergency shutdown bypass valve seal integrity compromised with visible weeping of seal fluid."
    ])
    for f in raw_findings:
        story.append(Paragraph(f"• {f}", bullet_style))
    story.append(Spacer(1, 6))

    # 5. Section 3: Compliance Gaps Table
    story.append(Paragraph("3. Compliance Gaps & Authoritative Standard Citations", section_style))
    raw_gaps = data.get("compliance_gaps", [
        ("Discharge Flange Wall Thinning", "Safety SOP - Section 4.2 Emergency Shutdown Systems (p.12)", "CRITICAL NON-COMPLIANCE"),
        ("PRV-204 Recertification Overdue", "Equipment Standards - Section 11.4 Relief Valve Recertification (p.56)", "MAJOR GAP"),
        ("Seal Integrity Weeping", "Maintenance Manual - Section 8.1 Flange Integrity & Bolt Torquing (p.34)", "MODERATE GAP"),
    ])

    gap_table_data = [[
        Paragraph("Observed Finding / Defect", table_header_style),
        Paragraph("Authoritative SOP Citation", table_header_style),
        Paragraph("Compliance Rating", table_header_style),
    ]]

    for item in raw_gaps:
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            d_val, c_val, r_val = item[0], item[1], item[2]
        else:
            d_val, c_val, r_val = str(item), "Standard SOP", "NON-COMPLIANCE"

        r_style = table_cell_alert if ("CRITICAL" in str(r_val) or "NON-COMPLIANCE" in str(r_val)) else table_cell_style
        gap_table_data.append([
            Paragraph(str(d_val), table_cell_style),
            Paragraph(str(c_val), table_cell_style),
            Paragraph(str(r_val), r_style),
        ])

    gap_table = Table(gap_table_data, colWidths=[2.4 * inch, 3.1 * inch, 1.5 * inch])
    gap_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY_COLOR),
            ("BOX", (0, 0), (-1, -1), 0.5, NAVY_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT_ROW_COLOR]),
        ])
    )
    story.append(gap_table)
    story.append(Spacer(1, 10))

    # 6. Section 4: Actionable Recommendations
    story.append(Paragraph("4. Actionable Engineering Recommendations", section_style))
    raw_recs = data.get("recommendations", [
        "Initiate immediate scheduled depressurization and replacement of flange bolting assembly.",
        "Perform off-line hydrostatic bench testing and recertification for PRV-204 within 48 hours.",
        "Replace primary mechanical seal pack on pump P-102A prior to resuming continuous service."
    ])
    for idx, rec in enumerate(raw_recs, start=1):
        story.append(Paragraph(f"<b>4.{idx}</b> {rec}", bullet_style))
    story.append(Spacer(1, 10))

    # 7. Section 5: Engineering Review Sign-off Block
    prep_status = data.get("status") or "Analyzed on-premise"
    sign_table_data = [
        [
            Paragraph(f"<b>Prepared Autonomously By:</b><br/>Sovereign AI Workbench ({prep_status})", body_style),
            Paragraph("<b>Reviewed & Endorsed By:</b><br/><br/>___________________________________<br/>Lead Technical Reviewer", body_style),
        ]
    ]
    sign_table = Table(sign_table_data, colWidths=[3.5 * inch, 3.5 * inch])
    sign_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), ICE_COLOR),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FAFAFA")),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(KeepTogether([sign_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
