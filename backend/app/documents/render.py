"""Render CV data and cover letters to professional, ATS-friendly PDF and DOCX.

Design goals (blueprint sections 32 & 33):
- Single column, real selectable text, standard section headings, no tables /
  text boxes / images — the layout ATS parsers read most reliably, in EVERY
  template below (a template changes typography/colour/order, never the
  underlying ATS-safe structure).
- Polished and HR-attractive: a clean branded header, clear section rules,
  achievement bullet points, and consistent typography.
- Five distinct visual templates (blueprint: CV template gallery) — Executive,
  Professional, Modern, ATS PRO (minimal), Academic/Technical — implemented as
  one rendering engine parameterised by a small style config per template,
  rather than five near-duplicate files, so the ATS-safety guarantees and bug
  fixes apply to all of them identically.
PDF via ReportLab, DOCX via python-docx.
"""
from __future__ import annotations

import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
)

# Brand palette (kept subtle so the document still reads as a serious CV).
NAVY = colors.HexColor("#0b2447")
TEAL = colors.HexColor("#0f766e")
GOLD = colors.HexColor("#f5b301")
GREY = colors.HexColor("#5b6675")
BLACK = colors.HexColor("#111111")
CHARCOAL = colors.HexColor("#333333")
FOREST = colors.HexColor("#1f3d2b")

# ---- Template gallery --------------------------------------------------------
# Every template renders the exact same single-column, table-free, image-free
# structure (what makes a CV ATS-safe) — only typography, colour, header
# layout and section order change. "ats_clean" is kept as an alias for
# "ats_pro" so CVVersion rows created before this template gallery existed
# (which default to "ats_clean" at the database level) keep rendering.
DEFAULT_SECTION_ORDER = ["summary", "skills", "experience", "education", "certifications", "additional"]
ACADEMIC_SECTION_ORDER = ["summary", "education", "certifications", "experience", "skills", "additional"]

TEMPLATES: dict[str, dict] = {
    "executive": {
        "label": "Executive", "description": "Centred header, generous spacing, a formal serif — for senior and leadership roles.",
        "font": "Times-Roman", "font_bold": "Times-Bold", "font_italic": "Times-Italic",
        "name_color": NAVY, "role_color": GOLD,
        "section_color": NAVY, "rule_color": GOLD, "contact_color": GREY,
        "header_align": "center", "section_style": "rule", "section_order": DEFAULT_SECTION_ORDER,
        "use_color": True,
    },
    "professional": {
        "label": "Professional", "description": "The classic Sospana Sonke design — navy and teal, clean and versatile.",
        "font": "Helvetica", "font_bold": "Helvetica-Bold", "font_italic": "Helvetica-Oblique",
        "name_color": NAVY, "role_color": TEAL, "section_color": NAVY, "rule_color": GOLD,
        "contact_color": GREY, "header_align": "left", "section_style": "rule",
        "section_order": DEFAULT_SECTION_ORDER, "use_color": True,
    },
    "modern": {
        "label": "Modern", "description": "Teal-forward, tighter spacing and bold small-caps section labels — a contemporary look.",
        "font": "Helvetica", "font_bold": "Helvetica-Bold", "font_italic": "Helvetica-Oblique",
        "name_color": TEAL, "role_color": NAVY, "section_color": TEAL, "rule_color": TEAL,
        "contact_color": GREY, "header_align": "left", "section_style": "bar",
        "section_order": DEFAULT_SECTION_ORDER, "use_color": True,
    },
    "ats_pro": {
        "label": "ATS PRO (minimal)", "description": "Pure black text, no colour or rules — the single safest choice for automated screening.",
        "font": "Helvetica", "font_bold": "Helvetica-Bold", "font_italic": "Helvetica-Oblique",
        "name_color": BLACK, "role_color": BLACK, "section_color": BLACK, "rule_color": BLACK,
        "contact_color": CHARCOAL, "header_align": "left", "section_style": "plain",
        "section_order": DEFAULT_SECTION_ORDER, "use_color": False,
    },
    "academic": {
        "label": "Academic / Technical", "description": "Leads with qualifications and certifications — for academic, research and technical roles.",
        "font": "Times-Roman", "font_bold": "Times-Bold", "font_italic": "Times-Italic",
        "name_color": FOREST, "role_color": GREY, "section_color": FOREST, "rule_color": FOREST,
        "contact_color": GREY, "header_align": "left", "section_style": "rule",
        "section_order": ACADEMIC_SECTION_ORDER, "use_color": True,
    },
}
TEMPLATES["ats_clean"] = TEMPLATES["ats_pro"]  # backward-compatible alias


def template_style(template: str | None) -> dict:
    return TEMPLATES.get((template or "professional").lower(), TEMPLATES["professional"])


def list_templates() -> list[dict]:
    """Public catalogue for the frontend's template gallery (name + description only)."""
    seen: set[str] = set()
    out = []
    for key, cfg in TEMPLATES.items():
        if cfg["label"] in seen:
            continue
        seen.add(cfg["label"])
        out.append({"id": key, "label": cfg["label"], "description": cfg["description"]})
    return out


def _contact_line(cv: dict) -> str:
    bits = [cv.get("email"), cv.get("phone")]
    loc = ", ".join(x for x in [cv.get("city"), cv.get("country")] if x)
    if loc:
        bits.append(loc)
    bits += [cv.get("linkedin_url"), cv.get("github_url"), cv.get("portfolio_url")]
    return "  |  ".join(b for b in bits if b)


def _exp_dates(e: dict) -> str:
    start = e.get("start_date") or ""
    end = "Present" if e.get("is_current") else (e.get("end_date") or "")
    return " – ".join(x for x in [str(start), str(end)] if x)


def _bullets(text) -> list[str]:
    """Split a free-text responsibilities/achievements field into clean bullets.

    Splits on newlines, semicolons, and bullet characters, and on sentence
    boundaries only when the text is one long run. Truthful: it reorganises the
    candidate's own words, never adds content.
    """
    if not text:
        return []
    raw = str(text).strip()
    parts = re.split(r"[\n;•·]|(?:(?<=[a-z0-9\)])\.\s+(?=[A-Z]))", raw)
    out = []
    for p in parts:
        s = (p or "").strip(" \t-–—.")
        if len(s) >= 2:
            out.append(s[0].upper() + s[1:])
    return out


# ---- PDF (ReportLab) --------------------------------------------------------

def render_cv_pdf(cv: dict, template: str | None = None) -> bytes:
    style = template_style(template)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.9 * cm, rightMargin=1.9 * cm,
                            title=(cv.get("full_name") or "Curriculum Vitae"))
    base = getSampleStyleSheet()
    name_align = TA_CENTER if style["header_align"] == "center" else TA_LEFT
    name_style = ParagraphStyle("Name", parent=base["Title"], fontName=style["font_bold"],
                                fontSize=22, textColor=style["name_color"], spaceAfter=1,
                                alignment=name_align, leading=24)
    role_style = ParagraphStyle("Role", parent=base["Normal"], fontName=style["font_bold"],
                                fontSize=11.5, textColor=style["role_color"], spaceAfter=3,
                                alignment=name_align)
    contact_style = ParagraphStyle("Contact", parent=base["Normal"], fontName=style["font"],
                                   fontSize=9, textColor=style["contact_color"], leading=13,
                                   alignment=name_align)
    section_style = ParagraphStyle("Section", parent=base["Heading2"], fontName=style["font_bold"],
                                   fontSize=11, textColor=style["section_color"], spaceBefore=12,
                                   spaceAfter=3, leading=13)
    body = ParagraphStyle("Body", parent=base["Normal"], fontName=style["font"], fontSize=10, leading=14.5)
    job_style = ParagraphStyle("Job", parent=body, fontName=style["font_bold"], fontSize=10.5, spaceBefore=6)
    meta_style = ParagraphStyle("Meta", parent=base["Normal"], fontName=style["font_italic"],
                                fontSize=9, textColor=style["contact_color"], spaceAfter=2)
    bullet_style = ParagraphStyle("Bullet", parent=body, fontSize=10, leading=14)

    def section(title: str):
        flow = [Paragraph(title.upper(), section_style)]
        if style["section_style"] == "rule":
            flow.append(HRFlowable(width="100%", thickness=1, color=style["rule_color"], spaceBefore=1, spaceAfter=5))
        elif style["section_style"] == "bar":
            flow.append(HRFlowable(width="18%", thickness=2.4, color=style["rule_color"], spaceBefore=1,
                                   spaceAfter=6, hAlign="LEFT"))
        else:  # "plain" (ATS PRO): no rule at all, just spacing — maximal parser safety.
            flow.append(Spacer(1, 4))
        return flow

    def bullet_list(items: list[str]):
        bullet_color = style["rule_color"] if style["use_color"] else BLACK
        return ListFlowable(
            [ListItem(Paragraph(escape(i), bullet_style), leftIndent=10, value=None) for i in items],
            bulletType="bullet", bulletChar="•", bulletColor=bullet_color, bulletFontSize=9,
            leftIndent=12, spaceBefore=1, spaceAfter=1,
        )

    story = [Paragraph(escape(cv.get("full_name") or "Curriculum Vitae"), name_style)]
    role = cv.get("target_vacancy_title") or cv.get("current_occupation")
    if role and str(role).strip().lower() != "the role":
        story.append(Paragraph(escape(str(role)), role_style))
    contact = _contact_line(cv)
    if contact:
        story.append(Paragraph(escape(contact), contact_style))
    story.append(HRFlowable(width="100%", thickness=2 if style["use_color"] else 1,
                            color=(style["name_color"] if style["use_color"] else BLACK),
                            spaceBefore=6, spaceAfter=2))

    def build_summary():
        out = []
        if cv.get("summary"):
            out += section("Professional Summary")
            out.append(Paragraph(escape(cv["summary"]), body))
        return out

    def build_skills():
        out = []
        if cv.get("skills"):
            out += section("Core Skills")
            out.append(Paragraph(escape("  •  ".join(cv["skills"])), body))
        return out

    def build_experience():
        out = []
        if cv.get("experience"):
            out += section("Work Experience")
            for e in cv["experience"]:
                header = " — ".join(x for x in [e.get("position"), e.get("employer")] if x)
                if header:
                    out.append(Paragraph(escape(header), job_style))
                meta = "  ·  ".join(x for x in [_exp_dates(e), e.get("industry")] if x)
                if meta:
                    out.append(Paragraph(escape(meta), meta_style))
                resp = _bullets(e.get("responsibilities"))
                if resp:
                    out.append(bullet_list(resp))
                achv = _bullets(e.get("achievements"))
                if achv:
                    out.append(Paragraph("<b>Key achievements</b>", meta_style))
                    out.append(bullet_list(achv))
        return out

    def build_education():
        out = []
        if cv.get("education"):
            out += section("Education")
            for ed in cv["education"]:
                line = " — ".join(x for x in [ed.get("qualification"), ed.get("institution")] if x)
                if ed.get("completion_date"):
                    line += f"  ({ed['completion_date']})"
                out.append(Paragraph(escape(line or ed.get("institution", "")), body))
        return out

    def build_certifications():
        out = []
        if cv.get("certifications"):
            out += section("Certifications")
            for c in cv["certifications"]:
                line = " — ".join(x for x in [c.get("name"), c.get("issuing_organization")] if x)
                out.append(Paragraph(escape(line), body))
        return out

    def build_additional():
        extras = []
        if cv.get("languages"):
            extras.append("Languages: " + ", ".join(cv["languages"]))
        if cv.get("drivers_licence"):
            extras.append("Driver's licence: " + str(cv["drivers_licence"]))
        out = []
        if extras:
            out += section("Additional")
            for x in extras:
                out.append(Paragraph(escape(x), body))
        return out

    builders = {
        "summary": build_summary, "skills": build_skills, "experience": build_experience,
        "education": build_education, "certifications": build_certifications,
        "additional": build_additional,
    }
    for name in style["section_order"]:
        story += builders[name]()

    doc.build(story)
    return buf.getvalue()


# ---- DOCX (python-docx) -----------------------------------------------------

def render_cv_docx(cv: dict, template: str | None = None) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    style = template_style(template)

    def rgb(c) -> RGBColor:
        # Compute directly from the reportlab Color's 0-1 float channels rather
        # than relying on a particular hexval() string format.
        return RGBColor(int(round(c.red * 255)), int(round(c.green * 255)), int(round(c.blue * 255)))

    NAME_C, ROLE_C, SEC_C, CONTACT_C = rgb(style["name_color"]), rgb(style["role_color"]), \
        rgb(style["section_color"]), rgb(style["contact_color"])
    docx_font = "Georgia" if style["font"].startswith("Times") else "Calibri"

    d = Document()
    normal = d.styles["Normal"]
    normal.font.name = docx_font
    normal.font.size = Pt(10.5)

    align = WD_ALIGN_PARAGRAPH.CENTER if style["header_align"] == "center" else WD_ALIGN_PARAGRAPH.LEFT

    p = d.add_paragraph()
    p.alignment = align
    r = p.add_run(cv.get("full_name") or "Curriculum Vitae")
    r.bold = True
    r.font.size = Pt(22)
    r.font.color.rgb = NAME_C
    role = cv.get("target_vacancy_title") or cv.get("current_occupation")
    if role and str(role).strip().lower() != "the role":
        rp = d.add_paragraph()
        rp.alignment = align
        rr = rp.add_run(str(role))
        rr.bold = True
        rr.font.size = Pt(12)
        rr.font.color.rgb = ROLE_C
    contact = _contact_line(cv)
    if contact:
        cp = d.add_paragraph()
        cp.alignment = align
        cr = cp.add_run(contact)
        cr.font.size = Pt(9)
        cr.font.color.rgb = CONTACT_C

    def section(title: str):
        h = d.add_paragraph()
        hr = h.add_run(title.upper())
        hr.bold = True
        hr.font.size = Pt(11)
        hr.font.color.rgb = SEC_C
        if style["section_style"] != "plain":
            _bottom_border(d.add_paragraph(), style["rule_color"])

    def bullets(items):
        for i in items:
            d.add_paragraph(i, style="List Bullet")

    def do_summary():
        if cv.get("summary"):
            section("Professional Summary")
            d.add_paragraph(cv["summary"])

    def do_skills():
        if cv.get("skills"):
            section("Core Skills")
            d.add_paragraph("  •  ".join(cv["skills"]))

    def do_experience():
        if cv.get("experience"):
            section("Work Experience")
            for e in cv["experience"]:
                header = " — ".join(x for x in [e.get("position"), e.get("employer")] if x)
                hp = d.add_paragraph()
                hr = hp.add_run(header)
                hr.bold = True
                meta = "  ·  ".join(x for x in [_exp_dates(e), e.get("industry")] if x)
                if meta:
                    mp = d.add_paragraph()
                    mr = mp.add_run(meta)
                    mr.font.size = Pt(9)
                    mr.italic = True
                bullets(_bullets(e.get("responsibilities")))
                achv = _bullets(e.get("achievements"))
                if achv:
                    ap = d.add_paragraph()
                    ar = ap.add_run("Key achievements")
                    ar.bold = True
                    ar.font.size = Pt(9)
                    bullets(achv)

    def do_education():
        if cv.get("education"):
            section("Education")
            for ed in cv["education"]:
                line = " — ".join(x for x in [ed.get("qualification"), ed.get("institution")] if x)
                if ed.get("completion_date"):
                    line += f"  ({ed['completion_date']})"
                d.add_paragraph(line or ed.get("institution", ""))

    def do_certifications():
        if cv.get("certifications"):
            section("Certifications")
            for c in cv["certifications"]:
                d.add_paragraph(" — ".join(x for x in [c.get("name"), c.get("issuing_organization")] if x))

    def do_additional():
        if cv.get("languages") or cv.get("drivers_licence"):
            section("Additional")
            if cv.get("languages"):
                d.add_paragraph("Languages: " + ", ".join(cv["languages"]))
            if cv.get("drivers_licence"):
                d.add_paragraph("Driver's licence: " + str(cv["drivers_licence"]))

    doers = {
        "summary": do_summary, "skills": do_skills, "experience": do_experience,
        "education": do_education, "certifications": do_certifications, "additional": do_additional,
    }
    for name in style["section_order"]:
        doers[name]()

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _bottom_border(paragraph, color=GOLD):
    """Add a thin bottom border to a paragraph (used as a section rule)."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    hexcolor = "%02x%02x%02x" % (int(round(color.red * 255)), int(round(color.green * 255)),
                                 int(round(color.blue * 255)))
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), hexcolor)
    pbdr.append(bottom)
    pPr.append(pbdr)


# ---- Cover letter -----------------------------------------------------------

def render_letter_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2.2 * cm, rightMargin=2.2 * cm, title="Cover Letter")
    base = getSampleStyleSheet()
    body = ParagraphStyle("LetterBody", parent=base["Normal"], fontSize=11, leading=16, spaceAfter=8)
    story = []
    for para in text.split("\n\n"):
        story.append(Paragraph(escape(para).replace("\n", "<br/>"), body))
    doc.build(story)
    return buf.getvalue()


def render_letter_docx(text: str) -> bytes:
    from docx import Document
    from docx.shared import Pt
    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    for para in text.split("\n\n"):
        d.add_paragraph(para)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
