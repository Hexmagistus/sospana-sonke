"""Phase 3 & 6 — premium, ATS-safe rendering of a rebuilt CV to DOCX and PDF.

Layout rules (from the brief, enforced for both formats):
- one column, no tables, text boxes, images, icons, rating bars or charts;
- name and contact details in the document BODY (nothing in header/footer);
- standard section headings an ATS recognises;
- real list bullets (Word "List Bullet" style / ReportLab bullet list);
- restrained palette: navy headings, charcoal body text, one teal accent rule;
- consistent date format ("Mon YYYY – Mon YYYY") and spacing.

Both renderers walk the same ``sections(cv)`` list so the DOCX and PDF can
never drift apart in content or order.
"""
from __future__ import annotations

import io
import re
from xml.sax.saxutils import escape

NAVY = (0x1B, 0x2A, 0x4A)
CHARCOAL = (0x33, 0x3D, 0x4A)
ACCENT = (0x0F, 0x76, 0x6E)
MUTED = (0x5B, 0x66, 0x75)

_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def _safe(v):
    if isinstance(v, str):
        return _XML_ILLEGAL.sub("", v)
    if isinstance(v, dict):
        return {k: _safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_safe(x) for x in v]
    return v


def contact_line(cv: dict) -> str:
    bits = [cv.get("location"), cv.get("phone"), cv.get("email"), cv.get("linkedin_url"), *(cv.get("links") or [])]
    return "  |  ".join(b for b in bits if b)


def dates(e: dict) -> str:
    start, end = e.get("start") or "", e.get("end") or ("Present" if e.get("is_current") else "")
    return " – ".join(x for x in [start, end] if x)


STATUS_TEXT = {
    "in_progress": "In progress",
    "awaiting_conferral": "Completed – awaiting conferral",
    "unverified": "Status to be confirmed",
    "completed": "",
}


def sections(cv: dict) -> list[dict]:
    """Ordered, renderer-neutral section model.

    Each section: {"title": str, "blocks": [block]} where a block is one of
    {"type": "para", "text"}, {"type": "labelled", "label", "text"},
    {"type": "entry", "title", "meta"}, {"type": "bullets", "items"}.
    """
    out: list[dict] = []

    if cv.get("summary"):
        out.append({"title": "Professional Summary", "blocks": [{"type": "para", "text": cv["summary"]}]})

    comp = cv.get("competencies") or {}
    if comp:
        out.append({"title": "Core Competencies", "blocks": [
            {"type": "labelled", "label": g, "text": ", ".join(ts)} for g, ts in comp.items() if ts]})

    if cv.get("experience"):
        blocks = []
        for e in cv["experience"]:
            title = e.get("position") or e.get("employer") or "Role"
            meta = "  |  ".join(x for x in [e.get("employer") if e.get("position") else None,
                                             e.get("location"), dates(e)] if x)
            blocks.append({"type": "entry", "title": title, "meta": meta})
            if e.get("bullets"):
                blocks.append({"type": "bullets", "items": e["bullets"]})
        out.append({"title": "Professional Experience", "blocks": blocks})

    def edu_blocks(rows: list[dict], show_status: bool) -> list[dict]:
        blocks = []
        for ed in rows:
            title = ed.get("qualification") or ed.get("institution") or ""
            status = STATUS_TEXT.get(ed.get("status") or "", "") if show_status else ""
            meta = "  |  ".join(x for x in [ed.get("institution") if ed.get("qualification") else None,
                                             ed.get("date_text"), status] if x)
            blocks.append({"type": "entry", "title": title, "meta": meta})
        return blocks

    if cv.get("education"):
        out.append({"title": "Education", "blocks": edu_blocks(cv["education"], False)})
    if cv.get("current_studies"):
        out.append({"title": "Current Studies", "blocks": edu_blocks(cv["current_studies"], True)})

    cert_blocks = []

    def cert_line(c: dict) -> str:
        bits = [c.get("name"), c.get("issuer"), c.get("year")]
        return " – ".join(b for b in bits if b)

    if cv.get("certifications"):
        cert_blocks.append({"type": "labelled", "label": "Certifications",
                            "text": "; ".join(cert_line(c) for c in cv["certifications"])})
    if cv.get("in_progress_certs"):
        cert_blocks.append({"type": "labelled", "label": "In progress",
                            "text": "; ".join(cert_line(c) for c in cv["in_progress_certs"])})
    if cv.get("short_courses"):
        cert_blocks.append({"type": "labelled", "label": "Short courses",
                            "text": "; ".join(cert_line(c) for c in cv["short_courses"])})
    if cv.get("registrations"):
        cert_blocks.append({"type": "labelled", "label": "Professional registrations and memberships",
                            "text": "; ".join(cert_line(c) for c in cv["registrations"])})
    if cert_blocks:
        out.append({"title": "Certifications and Professional Development", "blocks": cert_blocks})

    if cv.get("software"):
        out.append({"title": "Software and Digital Skills",
                    "blocks": [{"type": "para", "text": ", ".join(cv["software"])}]})
    if cv.get("projects"):
        out.append({"title": "Selected Projects", "blocks": [{"type": "bullets", "items": cv["projects"]}]})
    if cv.get("achievements"):
        out.append({"title": "Achievements", "blocks": [{"type": "bullets", "items": cv["achievements"]}]})

    extra = []
    if cv.get("languages"):
        extra.append({"type": "labelled", "label": "Languages", "text": ", ".join(cv["languages"])})
    if cv.get("drivers_licence"):
        extra.append({"type": "labelled", "label": "Driver’s licence", "text": cv["drivers_licence"]})
    if extra:
        out.append({"title": "Additional Information", "blocks": extra})
    return out


# ---- DOCX -------------------------------------------------------------------------

def render_docx(cv: dict, compact: bool = False) -> bytes:
    cv = _safe(cv)
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor, Cm

    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(1.9)
    sec.top_margin = sec.bottom_margin = Cm(1.5 if compact else 1.7)

    body_pt = 10 if compact else 10.5
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(body_pt)
    normal.font.color.rgb = RGBColor(*CHARCOAL)
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.08

    h = doc.styles["Heading 1"]
    h.font.name = "Calibri"
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    h.element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    h.element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    h.font.size = Pt(11.5)
    h.font.bold = True
    h.font.all_caps = True
    h.font.color.rgb = RGBColor(*NAVY)
    h.paragraph_format.space_before = Pt(9 if compact else 12)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True

    lb = doc.styles["List Bullet"]
    lb.font.name = "Calibri"
    lb.font.size = Pt(body_pt)
    lb.paragraph_format.space_after = Pt(1)

    def rule(paragraph, color=ACCENT, size=12):
        p_pr = paragraph._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), str(size))
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "%02X%02X%02X" % color)
        bdr.append(bottom)
        p_pr.append(bdr)

    p = doc.add_paragraph()
    r = p.add_run(cv.get("full_name") or "Curriculum Vitae")
    r.bold = True
    r.font.size = Pt(24)
    r.font.color.rgb = RGBColor(*NAVY)
    p.paragraph_format.space_after = Pt(0)
    if cv.get("headline"):
        p = doc.add_paragraph()
        r = p.add_run(cv["headline"])
        r.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(*ACCENT)
        p.paragraph_format.space_after = Pt(2)
    cl = contact_line(cv)
    p = doc.add_paragraph()
    r = p.add_run(cl)
    r.font.size = Pt(9.5)
    r.font.color.rgb = RGBColor(*MUTED)
    p.paragraph_format.space_after = Pt(4)
    rule(p, ACCENT, 12)

    for s in sections(cv):
        hp = doc.add_paragraph(s["title"], style="Heading 1")
        rule(hp, (0xC9, 0xD2, 0xDE), 6)
        for b in s["blocks"]:
            if b["type"] == "para":
                para = doc.add_paragraph(b["text"])
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            elif b["type"] == "labelled":
                para = doc.add_paragraph()
                lr = para.add_run(b["label"] + ": ")
                lr.bold = True
                lr.font.color.rgb = RGBColor(*NAVY)
                para.add_run(b["text"])
            elif b["type"] == "entry":
                para = doc.add_paragraph()
                para.paragraph_format.space_before = Pt(5)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.keep_with_next = True
                tr = para.add_run(b["title"])
                tr.bold = True
                tr.font.size = Pt(body_pt + 0.5)
                tr.font.color.rgb = RGBColor(*NAVY)
                if b.get("meta"):
                    mp = doc.add_paragraph()
                    mp.paragraph_format.space_after = Pt(2)
                    mp.paragraph_format.keep_with_next = True
                    mr = mp.add_run(b["meta"])
                    mr.italic = True
                    mr.font.size = Pt(body_pt - 0.5)
                    mr.font.color.rgb = RGBColor(*MUTED)
            elif b["type"] == "bullets":
                for it in b["items"]:
                    doc.add_paragraph(it, style="List Bullet")

    props = doc.core_properties
    props.title = f"{cv.get('full_name') or 'Candidate'} — CV"
    props.author = cv.get("full_name") or ""
    props.subject = cv.get("headline") or ""
    props.comments = ""
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---- PDF --------------------------------------------------------------------------

_FONTS: dict[str, str] | None = None


def _pdf_fonts() -> dict[str, str]:
    """Carlito (SIL OFL, metric-compatible with Calibri — matching the DOCX) is
    bundled so the PDF looks like the Word file AND extracts cleanly: a
    TrueType font carries a ToUnicode map, so bullets and en dashes come back as
    “•” and “–” for an ATS instead of the junk the base-14 Helvetica produces.
    Falls back to Helvetica if the font files are missing."""
    global _FONTS
    if _FONTS is not None:
        return _FONTS
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    here = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
    try:
        for name, file in (("Carlito", "Carlito-Regular.ttf"), ("Carlito-Bold", "Carlito-Bold.ttf"),
                           ("Carlito-Italic", "Carlito-Italic.ttf")):
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, os.path.join(here, file)))
        from reportlab.lib.fonts import addMapping
        addMapping("Carlito", 0, 0, "Carlito")
        addMapping("Carlito", 1, 0, "Carlito-Bold")
        addMapping("Carlito", 0, 1, "Carlito-Italic")
        addMapping("Carlito", 1, 1, "Carlito-Bold")
        _FONTS = {"regular": "Carlito", "bold": "Carlito-Bold", "italic": "Carlito-Italic"}
    except Exception:
        _FONTS = {"regular": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique"}
    return _FONTS

def render_pdf(cv: dict, compact: bool = False) -> bytes:
    cv = _safe(cv)
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether

    def c(rgb):
        return colors.Color(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.9 * cm, rightMargin=1.9 * cm,
                            topMargin=(1.4 if compact else 1.6) * cm, bottomMargin=1.5 * cm,
                            title=f"{cv.get('full_name') or 'Candidate'} — CV",
                            author=cv.get("full_name") or "", subject=cv.get("headline") or "")
    F = _pdf_fonts()
    body_pt = 10.2 if compact else 10.8
    lead = body_pt * 1.42
    name_s = ParagraphStyle("name", fontName=F["bold"], fontSize=25, leading=29, textColor=c(NAVY))
    head_s = ParagraphStyle("headline", fontName=F["bold"], fontSize=12.5, leading=16, textColor=c(ACCENT))
    contact_s = ParagraphStyle("contact", fontName=F["regular"], fontSize=9.8, leading=13, textColor=c(MUTED))
    sec_s = ParagraphStyle("sec", fontName=F["bold"], fontSize=11.6, leading=14, textColor=c(NAVY),
                           spaceBefore=8 if compact else 11, spaceAfter=1)
    body_s = ParagraphStyle("body", fontName=F["regular"], fontSize=body_pt, leading=lead, textColor=c(CHARCOAL))
    entry_s = ParagraphStyle("entry", parent=body_s, fontName=F["bold"], fontSize=body_pt + 0.6,
                             textColor=c(NAVY), spaceBefore=5)
    meta_s = ParagraphStyle("meta", parent=body_s, fontName=F["italic"], fontSize=body_pt - 0.6,
                            textColor=c(MUTED), spaceAfter=2)
    bullet_s = ParagraphStyle("bullet", parent=body_s, leading=lead - 0.6, leftIndent=13, bulletIndent=2,
                              bulletFontName=F["regular"], bulletFontSize=body_pt, bulletColor=c(ACCENT),
                              spaceAfter=0.6)

    story = [Paragraph(escape(cv.get("full_name") or "Curriculum Vitae"), name_s)]
    if cv.get("headline"):
        story.append(Paragraph(escape(cv["headline"]), head_s))
    cl = contact_line(cv)
    if cl:
        story.append(Paragraph(escape(cl), contact_s))
    story.append(HRFlowable(width="100%", thickness=1.6, color=c(ACCENT), spaceBefore=5, spaceAfter=2))

    for s in sections(cv):
        heading = [Paragraph(escape(s["title"].upper()), sec_s),
                   HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#C9D2DE"),
                              spaceBefore=1, spaceAfter=4)]
        state = {"first": True}

        def emit(flow: list, keep: list | None = None):
            """Append flowables; the section heading and an entry's title/meta are
            kept on the same page as the first thing that follows them."""
            keep = keep or []
            if state["first"]:
                story.append(KeepTogether(heading + keep + flow[:1]))
                story.extend(flow[1:])
                state["first"] = False
            elif keep:
                story.append(KeepTogether(keep + flow[:1]))
                story.extend(flow[1:])
            else:
                story.extend(flow)

        pending: list = []
        for b in s["blocks"]:
            if b["type"] == "entry":
                if pending:
                    emit([], pending)
                pending = [Paragraph(escape(b["title"]), entry_s)]
                if b.get("meta"):
                    pending.append(Paragraph(escape(b["meta"]), meta_s))
                continue
            if b["type"] == "para":
                flow = [Paragraph(escape(b["text"]), body_s)]
            elif b["type"] == "labelled":
                flow = [Paragraph(f"<font name='{F['bold']}' color='#1B2A4A'>{escape(b['label'])}:</font> "
                                  f"{escape(b['text'])}", ParagraphStyle("lab", parent=body_s, spaceAfter=2))]
            else:  # bullets
                flow = [Paragraph(escape(i), bullet_s, bulletText="•") for i in b["items"]]
            emit(flow, pending)
            pending = []
        if pending:
            emit([], pending)
        if state["first"]:
            story.extend(heading)
        story.append(Spacer(1, 1))

    doc.build(story)
    return buf.getvalue()
