"""Render CV data and cover letters to ATS-friendly PDF and DOCX.

Deliberately simple, single-column, standard-heading layouts with no tables,
text boxes, columns, or images — the layout ATS parsers read most reliably
(blueprint sections 32 & 33). PDF via ReportLab, DOCX via python-docx.
"""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def _contact_line(cv: dict) -> str:
    bits = [cv.get("email"), cv.get("phone"), cv.get("city")]
    bits += [cv.get("linkedin_url"), cv.get("github_url"), cv.get("portfolio_url")]
    return "  |  ".join(b for b in bits if b)


def _exp_dates(e: dict) -> str:
    start = e.get("start_date") or ""
    end = "Present" if e.get("is_current") else (e.get("end_date") or "")
    return " – ".join(x for x in [str(start), str(end)] if x)


# ---- PDF (ReportLab) --------------------------------------------------------

def render_cv_pdf(cv: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            leftMargin=1.8 * cm, rightMargin=1.8 * cm, title="CV")
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=styles["Title"], fontSize=18, spaceAfter=2, alignment=TA_LEFT)
    h = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)

    story = [Paragraph(escape(cv.get("full_name") or "Curriculum Vitae"), name_style)]
    contact = _contact_line(cv)
    if contact:
        story.append(Paragraph(escape(contact), body))

    if cv.get("summary"):
        story += [Paragraph("Professional Summary", h), Paragraph(escape(cv["summary"]), body)]

    if cv.get("skills"):
        story += [Paragraph("Skills", h), Paragraph(escape(", ".join(cv["skills"])), body)]

    if cv.get("experience"):
        story.append(Paragraph("Work Experience", h))
        for e in cv["experience"]:
            header = " — ".join(x for x in [e.get("position"), e.get("employer")] if x)
            dates = _exp_dates(e)
            line = header + (f"  ({dates})" if dates else "")
            story.append(Paragraph(f"<b>{escape(line)}</b>", body))
            if e.get("responsibilities"):
                story.append(Paragraph(escape(e["responsibilities"]), body))
            if e.get("achievements"):
                story.append(Paragraph("Achievements: " + escape(e["achievements"]), body))
            story.append(Spacer(1, 4))

    if cv.get("education"):
        story.append(Paragraph("Education", h))
        for ed in cv["education"]:
            line = " — ".join(x for x in [ed.get("qualification"), ed.get("institution")] if x)
            if ed.get("completion_date"):
                line += f"  ({ed['completion_date']})"
            story.append(Paragraph(escape(line or ed.get("institution", "")), body))

    if cv.get("certifications"):
        story.append(Paragraph("Certifications", h))
        for c in cv["certifications"]:
            line = " — ".join(x for x in [c.get("name"), c.get("issuing_organization")] if x)
            story.append(Paragraph(escape(line), body))

    extras = []
    if cv.get("languages"):
        extras.append("Languages: " + ", ".join(cv["languages"]))
    if cv.get("drivers_licence"):
        extras.append("Driver's licence: " + str(cv["drivers_licence"]))
    if extras:
        story.append(Paragraph("Additional", h))
        for x in extras:
            story.append(Paragraph(escape(x), body))

    doc.build(story)
    return buf.getvalue()


# ---- DOCX (python-docx) -----------------------------------------------------

def render_cv_docx(cv: dict) -> bytes:
    from docx import Document
    from docx.shared import Pt

    d = Document()
    d.add_heading(cv.get("full_name") or "Curriculum Vitae", level=0)
    contact = _contact_line(cv)
    if contact:
        d.add_paragraph(contact)

    def section(title):
        d.add_heading(title, level=1)

    if cv.get("summary"):
        section("Professional Summary")
        d.add_paragraph(cv["summary"])
    if cv.get("skills"):
        section("Skills")
        d.add_paragraph(", ".join(cv["skills"]))
    if cv.get("experience"):
        section("Work Experience")
        for e in cv["experience"]:
            header = " — ".join(x for x in [e.get("position"), e.get("employer")] if x)
            dates = _exp_dates(e)
            p = d.add_paragraph()
            run = p.add_run(header + (f"  ({dates})" if dates else ""))
            run.bold = True
            if e.get("responsibilities"):
                d.add_paragraph(e["responsibilities"])
            if e.get("achievements"):
                d.add_paragraph("Achievements: " + e["achievements"])
    if cv.get("education"):
        section("Education")
        for ed in cv["education"]:
            line = " — ".join(x for x in [ed.get("qualification"), ed.get("institution")] if x)
            if ed.get("completion_date"):
                line += f"  ({ed['completion_date']})"
            d.add_paragraph(line or ed.get("institution", ""))
    if cv.get("certifications"):
        section("Certifications")
        for c in cv["certifications"]:
            d.add_paragraph(" — ".join(x for x in [c.get("name"), c.get("issuing_organization")] if x))
    if cv.get("languages") or cv.get("drivers_licence"):
        section("Additional")
        if cv.get("languages"):
            d.add_paragraph("Languages: " + ", ".join(cv["languages"]))
        if cv.get("drivers_licence"):
            d.add_paragraph("Driver's licence: " + str(cv["drivers_licence"]))

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ---- Cover letter -----------------------------------------------------------

def render_letter_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm, title="Cover Letter")
    body = ParagraphStyle("Body", parent=getSampleStyleSheet()["Normal"], fontSize=11, leading=16)
    story = []
    for para in text.split("\n\n"):
        story.append(Paragraph(escape(para).replace("\n", "<br/>"), body))
        story.append(Spacer(1, 8))
    doc.build(story)
    return buf.getvalue()


def render_letter_docx(text: str) -> bytes:
    from docx import Document
    d = Document()
    for para in text.split("\n\n"):
        d.add_paragraph(para)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
