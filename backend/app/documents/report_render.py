"""Render the candidate intelligence report to PDF (blueprint section 18)."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def render_report_pdf(stats: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            leftMargin=1.8 * cm, rightMargin=1.8 * cm, title="Job Application Report")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Title"], fontSize=18)
    h = ParagraphStyle("H", parent=styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14)

    story = [Paragraph("Job Application Intelligence Report", title),
             Paragraph(f"Candidate: {escape(stats.get('candidate_name',''))}", body),
             Paragraph(f"Date: {escape(str(stats.get('date','')))}", body), Spacer(1, 8)]

    summary = [
        ["Vacancies analysed", stats.get("vacancies_analyzed", 0)],
        ["Qualified (apply/review)", stats.get("qualified", 0)],
        ["Rejected", stats.get("rejected", 0)],
        ["CVs generated", stats.get("cvs_generated", 0)],
        ["Cover letters generated", stats.get("cover_letters_generated", 0)],
        ["Applications submitted", stats.get("applications_submitted", 0)],
        ["Requiring your action", stats.get("requiring_action", 0)],
    ]
    t = Table([["Metric", "Count"]] + [[k, str(v)] for k, v in summary], colWidths=[10 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))
    story += [t, Spacer(1, 6)]

    top = stats.get("top_applications") or []
    if top:
        story.append(Paragraph("Top matches", h))
        for i, m in enumerate(top, 1):
            line = f"{i}. {m.get('title','')} — {m.get('company','')}  ·  Match: {m.get('score','')}%  ·  {m.get('status','')}"
            story.append(Paragraph(escape(line), body))

    rejected = stats.get("rejected_examples") or []
    if rejected:
        story.append(Paragraph("Examples of rejected vacancies (and why)", h))
        for m in rejected:
            line = f"{m.get('title','')} — {m.get('company','')}: {m.get('reason','No specific reason recorded.')}"
            story.append(Paragraph(escape(line), body))

    story += [Spacer(1, 10), Paragraph(
        "This report is advisory. Matching is a guide, not a guarantee of interviews or employment; "
        "employers make all hiring decisions.", ParagraphStyle("F", parent=body, fontSize=8,
                                                               textColor=colors.HexColor("#6b7280")))]
    doc.build(story)
    return buf.getvalue()
