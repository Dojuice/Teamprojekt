"""
PDF Report Service – Generates a corrected exam result as a downloadable PDF.

Uses ReportLab to create structured evaluation reports with:
- Header with student info and overall grade
- Per-task breakdown with scores and feedback
- Color-coded status indicators
- General feedback section
"""

import io
import os
from pathlib import Path
from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# Color scheme
BLUE = colors.HexColor("#1a73e8")
GREEN = colors.HexColor("#34a853")
RED = colors.HexColor("#ea4335")
YELLOW = colors.HexColor("#fbbc04")
GRAY = colors.HexColor("#5f6368")
LIGHT_GRAY = colors.HexColor("#f1f3f4")
WHITE = colors.white

# Status colors
STATUS_COLORS = {
    "korrekt": GREEN,
    "teilweise_korrekt": YELLOW,
    "falsch": RED,
    "nicht_beantwortet": GRAY,
}

STATUS_LABELS = {
    "korrekt": "Korrekt",
    "teilweise_korrekt": "Teilweise korrekt",
    "falsch": "Falsch",
    "nicht_beantwortet": "Nicht beantwortet",
}


def _get_styles():
    """Create custom paragraph styles for the report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=BLUE,
        spaceAfter=6 * mm,
    ))

    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=BLUE,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name="TaskHeader",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#202124"),
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    ))

    styles.add(ParagraphStyle(
        name="FeedbackText",
        parent=styles["Normal"],
        fontSize=9,
        textColor=GRAY,
        leftIndent=5 * mm,
        spaceBefore=1 * mm,
        spaceAfter=2 * mm,
    ))

    styles.add(ParagraphStyle(
        name="BodySmall",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#202124"),
    ))

    styles.add(ParagraphStyle(
        name="FooterStyle",
        parent=styles["Normal"],
        fontSize=7,
        textColor=GRAY,
        alignment=TA_CENTER,
    ))

    return styles


def generate_evaluation_pdf(evaluation: dict, filename: str = "Bewertung.pdf") -> bytes:
    """Generate a PDF report from an evaluation result.

    Args:
        evaluation: The structured evaluation dict from evaluate_exam().
        filename: Original exam filename for the header.

    Returns:
        PDF file content as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = _get_styles()
    story: list = []

    # --- Title ---
    story.append(Paragraph("AutoExam – Bewertungsergebnis", styles["ReportTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4 * mm))

    # --- Overview table ---
    student = evaluation.get("student_name", "Unbekannt")
    grade = evaluation.get("overall_grade", "–")
    score = evaluation.get("overall_score", 0)
    total_pts = evaluation.get("total_points", "–")
    max_pts = evaluation.get("max_points", "–")

    overview_data = [
        ["Klausur:", Paragraph(filename, styles["BodySmall"])],
        ["Student:", Paragraph(student, styles["BodySmall"])],
        ["Gesamtnote:", Paragraph(f"<b>{grade}</b>", styles["BodySmall"])],
        ["Gesamtpunktzahl:", Paragraph(f"<b>{total_pts} / {max_pts}</b> ({score}%)", styles["BodySmall"])],
    ]

    overview_table = Table(overview_data, colWidths=[35 * mm, 120 * mm])
    overview_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 4 * mm))

    # --- Score bar ---
    score_val = min(max(score, 0), 100)
    bar_color = GREEN if score_val >= 70 else (YELLOW if score_val >= 50 else RED)

    score_bar_data = [[""]]
    score_bar = Table(score_bar_data, colWidths=[155 * mm], rowHeights=[6 * mm])
    score_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), LIGHT_GRAY),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ("LINEBELOW", (0, 0), (0, 0), 0, WHITE),
    ]))
    story.append(score_bar)

    # Filled portion
    if score_val > 0:
        filled_width = max(155 * mm * score_val / 100, 10 * mm)
        filled_data = [[Paragraph(f"<b>{score_val}%</b>", ParagraphStyle(
            "ScoreLabel", parent=styles["Normal"], fontSize=8, textColor=WHITE, alignment=TA_CENTER
        ))]]
        filled_bar = Table(filled_data, colWidths=[filled_width], rowHeights=[6 * mm])
        filled_bar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), bar_color),
            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ]))
        story.append(Spacer(1, -6 * mm))  # Overlap with background bar
        story.append(filled_bar)

    story.append(Spacer(1, 6 * mm))

    # --- Tasks ---
    tasks = evaluation.get("tasks", [])
    if tasks:
        story.append(Paragraph("Aufgaben im Detail", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=2 * mm))

        for task in tasks:
            num = task.get("task_number", "?")
            title = task.get("task_title", "")
            pts = task.get("points_achieved", "?")
            pts_max = task.get("points_max", "?")
            status = task.get("status", "unbekannt")
            feedback = task.get("feedback", "")
            missing = task.get("missing_elements", [])
            correct = task.get("correct_elements", [])

            status_color = STATUS_COLORS.get(status, GRAY)
            status_label = STATUS_LABELS.get(status, status)

            # Task header row
            task_header = f"Aufgabe {num}"
            if title:
                task_header += f" – {title}"

            story.append(Paragraph(task_header, styles["TaskHeader"]))

            # Score and status row
            task_info_data = [[
                Paragraph(f"<b>{pts}/{pts_max} Punkte</b>", styles["BodySmall"]),
                Paragraph(f'<font color="{status_color.hexval()}">{status_label}</font>', styles["BodySmall"]),
            ]]
            task_info = Table(task_info_data, colWidths=[80 * mm, 75 * mm])
            task_info.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))
            story.append(task_info)

            # Feedback
            if feedback:
                story.append(Paragraph(feedback, styles["FeedbackText"]))

            # Correct elements
            if correct:
                correct_text = "✓ " + ", ".join(correct)
                story.append(Paragraph(
                    f'<font color="{GREEN.hexval()}">{correct_text}</font>',
                    styles["FeedbackText"]
                ))

            # Missing elements
            if missing:
                missing_text = "✗ Fehlend: " + ", ".join(missing)
                story.append(Paragraph(
                    f'<font color="{RED.hexval()}">{missing_text}</font>',
                    styles["FeedbackText"]
                ))

            story.append(HRFlowable(width="100%", thickness=0.3, color=LIGHT_GRAY, spaceAfter=1 * mm))

    # --- General feedback ---
    general = evaluation.get("general_feedback", "")
    if general:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Allgemeines Feedback", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=2 * mm))
        story.append(Paragraph(general, styles["BodySmall"]))

    # --- Strengths & Weaknesses ---
    strengths = evaluation.get("strengths", [])
    weaknesses = evaluation.get("weaknesses", [])

    if strengths or weaknesses:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Stärken & Verbesserungsmöglichkeiten", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=2 * mm))

        if strengths:
            story.append(Paragraph("<b>Stärken:</b>", styles["BodySmall"]))
            for s in strengths:
                story.append(Paragraph(f'<font color="{GREEN.hexval()}">  ✓ {s}</font>', styles["FeedbackText"]))

        if weaknesses:
            story.append(Paragraph("<b>Verbesserungsmöglichkeiten:</b>", styles["BodySmall"]))
            for w in weaknesses:
                story.append(Paragraph(f'<font color="{YELLOW.hexval()}">  → {w}</font>', styles["FeedbackText"]))

    # --- Footer ---
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=2 * mm))
    story.append(Paragraph("Generiert von AutoExam – KI-gestützte Klausurkorrektur", styles["FooterStyle"]))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_batch_zip(evaluations: List[dict]) -> bytes:
    """Generate a ZIP file containing individual PDF reports for each exam.

    Args:
        evaluations: List of dicts, each with 'filename', 'evaluation', 'status'.

    Returns:
        ZIP file content as bytes.
    """
    import zipfile

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in evaluations:
            if item.get("status") != "success":
                continue

            filename = item.get("filename", "unknown.pdf")
            evaluation = item.get("evaluation", {})

            # Generate PDF for this exam
            report_name = f"Bewertung_{os.path.splitext(filename)[0]}.pdf"
            pdf_bytes = generate_evaluation_pdf(evaluation, filename=filename)
            zf.writestr(report_name, pdf_bytes)

    zip_bytes = zip_buffer.getvalue()
    zip_buffer.close()
    return zip_bytes
