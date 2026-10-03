"""Render CV data and cover letters to PDF and DOCX.

The CV is one column of real text, in the same order a person reads it:
name, contact, then Summary, Experience, Education, Skills, Certifications,
Languages, Memberships and Additional — and only the sections the candidate
actually has. Nothing here invents a job, a date, a skill, or a photo.

A template changes type size, spacing and the navy/gold rules. It does not
change reading order, and it does not use tables, text boxes or images.
PDF uses the standard Helvetica family (the ATS-safe equivalent of Arial).
Word uses Calibri. Rules are dark enough to still show in black and white.

Older template ids still render: professional, executive and academic use
Classic; ats_pro and ats_clean use Compact.
"""
from __future__ import annotations

import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

NAVY = colors.HexColor("#0B2447")
GOLD = colors.HexColor("#8A6D2F")
INK = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#3D4754")

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SECTION_ORDER = [
    "summary", "experience", "education", "skills",
    "certifications", "languages", "memberships", "additional",
]
SECTION_TITLES = {
    "summary": "Summary",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "certifications": "Certifications",
    "languages": "Languages",
    "memberships": "Memberships",
    "additional": "Additional",
}

# XML 1.0 (which .docx is built on) forbids NUL and most C0 control characters.
_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def _xml_safe(value):
    """Recursively strip XML-illegal characters from every string in a CV/letter."""
    if isinstance(value, str):
        return _XML_ILLEGAL.sub("", value)
    if isinstance(value, dict):
        return {k: _xml_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_xml_safe(v) for v in value)
    return value


def _base_style(**over) -> dict:
    style = {
        "pdf_font": "Helvetica",
        "pdf_bold": "Helvetica-Bold",
        "pdf_italic": "Helvetica-Oblique",
        "docx_font": "Calibri",
        "name_size": 20,
        "name_leading": 24,
        "sub_size": 11,
        "sub_leading": 14,
        "contact_size": 9.5,
        "contact_leading": 12.5,
        "section_size": 11.5,
        "section_leading": 14,
        "section_before": 14,
        "section_before_first": 8,
        "body_size": 10.5,
        "body_leading": 15,
        "meta_size": 9.5,
        "meta_leading": 12.5,
        "bullet_size": 10.5,
        "bullet_leading": 14.5,
        "bullet_space": 1.25,
        "role_size": 11,
        "role_leading": 14,
        "role_gap": 9,
        "margin": 50,
        "top": 46,
        "bottom": 42,
        "header_bar": "full",
        "section_rule": "full",
        "date_short": False,
        "rule_gap": 6,
    }
    style.update(over)
    return style


TEMPLATES: dict[str, dict] = {
    "classic": _base_style(
        label="Classic",
        description="Navy headings, a gold rule and comfortable spacing. The default for most roles.",
    ),
    "modern": _base_style(
        label="Modern",
        description="A larger name, more space between sections, and a short gold accent.",
        name_size=22, name_leading=26, section_before=16, section_before_first=10,
        body_leading=15.5, margin=52, top=50, bottom=46, role_gap=10,
        header_bar="short", section_rule="short",
    ),
    "compact": _base_style(
        label="Compact",
        description="The same structure, set tighter so a longer record still fits on two pages.",
        name_size=16.5, name_leading=20, sub_size=10.5, sub_leading=13,
        contact_size=9, contact_leading=11.5, section_size=11, section_leading=13,
        section_before=9, section_before_first=5, body_size=10, body_leading=13,
        meta_size=9, meta_leading=11.5, bullet_size=10, bullet_leading=12.8,
        bullet_space=0.5, role_size=10.5, role_leading=13, role_gap=6,
        margin=40, top=36, bottom=34, header_bar="hairline", section_rule="hairline",
        date_short=True, rule_gap=3,
    ),
}

# Stored ids from before this gallery. They keep rendering; they are not listed.
_ALIASES = {
    "professional": "classic",
    "executive": "classic",
    "academic": "classic",
    "ats_pro": "compact",
    "ats_clean": "compact",
}


def template_style(template: str | None) -> dict:
    key = (template or "classic").strip().lower()
    key = _ALIASES.get(key, key)
    return TEMPLATES.get(key, TEMPLATES["classic"])


def list_templates() -> list[dict]:
    """Public catalogue for the template picker."""
    return [
        {"id": key, "label": cfg["label"], "description": cfg["description"]}
        for key, cfg in TEMPLATES.items()
    ]


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            text = _clean(item)
            if text:
                out.append(text)
        return out
    text = _clean(value)
    return [text] if text else []


def _is_current(entry: dict) -> bool:
    value = entry.get("is_current")
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def _format_date(value, short: bool) -> str:
    """Turn an ISO date into a month and year. Leave any other text as given."""
    raw = _clean(value)
    if not raw:
        return ""
    match = re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", raw)
    if not match:
        return raw
    month = int(match.group(2))
    if not 1 <= month <= 12:
        return match.group(1)
    names = _MONTHS_SHORT if short else _MONTHS
    return f"{names[month - 1]} {match.group(1)}"


def _exp_dates(entry: dict, short: bool) -> str:
    start = _format_date(entry.get("start_date"), short)
    end = "Present" if _is_current(entry) else _format_date(entry.get("end_date"), short)
    if start and end:
        return f"{start} – {end}"
    return start or end


def _bullets(text) -> list[str]:
    """Split a free-text field into clean bullets.

    Splits on newlines, semicolons and bullet characters, and on sentence
    boundaries only when the text is one long run. This reorganises the
    candidate's own words and never adds any.
    """
    if not text:
        return []
    if isinstance(text, (list, tuple)):
        out: list[str] = []
        for item in text:
            out.extend(_bullets(item))
        return out
    raw = str(text).strip()
    parts = re.split(r"[\n;•·]|(?:(?<=[a-z0-9\)])\.\s+(?=[A-Z]))", raw)
    out = []
    for part in parts:
        sentence = (part or "").strip(" \t-–—.")
        if len(sentence) >= 2:
            out.append(sentence[0].upper() + sentence[1:])
    return out


def _block(kind: str, text: str = "", **extra) -> dict:
    block = {"kind": kind, "text": text, "keep": False, "space_before": 0}
    block.update(extra)
    return block


def cv_blocks(cv: dict, template: str | None = None) -> list[dict]:
    """Linear reading order for one CV. Renderers must not reorder this."""
    style = template_style(template)
    short = style["date_short"]
    blocks: list[dict] = []
    identity: list[dict] = [
        _block("name", _clean(cv.get("full_name")) or "Curriculum Vitae", keep=True),
    ]
    role = _clean(cv.get("target_vacancy_title") or cv.get("current_occupation"))
    if role and role.lower() != "the role":
        identity.append(_block("subhead", role, keep=True))
    place = ", ".join(part for part in (_clean(cv.get("city")), _clean(cv.get("country"))) if part)
    if place:
        identity.append(_block("contact", place, keep=True))
    phone_email = "  ·  ".join(part for part in (_clean(cv.get("phone")), _clean(cv.get("email"))) if part)
    if phone_email:
        identity.append(_block("contact", phone_email, keep=True))
    for url in (_clean(cv.get("linkedin_url")), _clean(cv.get("github_url")), _clean(cv.get("portfolio_url"))):
        if url:
            identity.append(_block("contact", url, keep=True))
    identity[-1]["keep"] = False

    # Classic: gold bar, then the name. Modern: gold tick under the name.
    # Compact: one hairline under the contact block. One closing rule, not two.
    mode = style["header_bar"]
    if mode == "full":
        blocks.append(_block("bar", variant="full", keep=True))
        blocks.extend(identity)
        blocks.append(_block("bar", variant="close", keep=False))
    elif mode == "short":
        blocks.append(identity[0])
        blocks.append(_block("bar", variant="short", keep=True))
        blocks.extend(identity[1:])
        blocks.append(_block("bar", variant="close", keep=False))
    else:
        blocks.extend(identity)
        blocks.append(_block("bar", variant="hairline", keep=False))

    def add_section(key: str, body: list[dict]) -> None:
        if not body:
            return
        first = not any(b["kind"] == "heading" for b in blocks)
        blocks.append(_block(
            "heading", SECTION_TITLES[key], keep=True,
            space_before=style["section_before_first"] if first else style["section_before"],
        ))
        blocks.append(_block("bar", variant="section", keep=True))
        blocks.extend(body)

    summary = _clean(cv.get("summary"))
    if summary:
        add_section("summary", [_block("body", part) for part in re.split(r"\n+", summary) if part.strip()])

    experience_body: list[dict] = []
    shown_roles = 0
    for entry in cv.get("experience") or []:
        if not isinstance(entry, dict):
            continue
        position = _clean(entry.get("position") or entry.get("job_title"))
        employer = _clean(entry.get("employer") or entry.get("company"))
        dates = _exp_dates(entry, short)
        place_bits = [part for part in (
            _clean(entry.get("location") or entry.get("city")),
            _clean(entry.get("industry")),
        ) if part]
        resp = _bullets(entry.get("responsibilities"))
        achievements = _bullets(entry.get("achievements"))
        if achievements == resp:
            achievements = []
        technologies = _as_list(entry.get("technologies"))
        if not any([position, employer, dates, place_bits, resp, achievements, technologies]):
            continue
        follows = bool(place_bits or resp or achievements or technologies)
        experience_body.append(_block(
            "dated", left_bold=position, left_rest=employer, right=dates,
            keep=follows, space_before=2 if shown_roles == 0 else style["role_gap"],
        ))
        shown_roles += 1
        if place_bits:
            experience_body.append(_block(
                "meta", "  ·  ".join(place_bits), keep=bool(resp or achievements or technologies),
            ))
        for bullet in resp:
            experience_body.append(_block("bullet", bullet))
        if achievements:
            experience_body.append(_block("label", "Achievements", keep=True))
            for bullet in achievements:
                experience_body.append(_block("bullet", bullet))
        if technologies:
            experience_body.append(_block("meta", "Technologies: " + ", ".join(technologies)))
    add_section("experience", experience_body)

    education_body: list[dict] = []
    for index, entry in enumerate(cv.get("education") or []):
        if not isinstance(entry, dict):
            continue
        qualification = _clean(entry.get("qualification"))
        institution = _clean(entry.get("institution"))
        when = _format_date(entry.get("completion_date"), short)
        detail = "  ·  ".join(part for part in (
            _clean(entry.get("field_of_study")), _clean(entry.get("level")),
        ) if part)
        if not any([qualification, institution, when, detail]):
            continue
        education_body.append(_block(
            "dated", left_bold=qualification, left_rest=institution, right=when,
            keep=bool(detail), space_before=2 if index == 0 else style["role_gap"] - 2,
        ))
        if detail:
            education_body.append(_block("meta", detail))
    add_section("education", education_body)

    skills = _as_list(cv.get("skills"))
    if skills:
        add_section("skills", [_block("body", ", ".join(skills))])

    certification_body: list[dict] = []
    for index, entry in enumerate(cv.get("certifications") or []):
        if not isinstance(entry, dict):
            continue
        name = _clean(entry.get("name"))
        issuer = _clean(entry.get("issuing_organization") or entry.get("issuer"))
        issued = _format_date(entry.get("issue_date"), short)
        expires = _format_date(entry.get("expiry_date"), short)
        if issued and expires:
            when = f"{issued} – {expires}"
        elif issued:
            when = issued
        elif expires:
            when = f"Expires {expires}"
        else:
            when = ""
        if not any([name, issuer, when]):
            continue
        certification_body.append(_block(
            "dated", left_bold=name, left_rest=issuer, right=when,
            space_before=1 if index == 0 else 4,
        ))
    add_section("certifications", certification_body)

    languages = _as_list(cv.get("languages"))
    if languages:
        add_section("languages", [_block("body", ", ".join(languages))])

    memberships = _as_list(cv.get("professional_memberships"))
    if memberships:
        add_section("memberships", [_block("body", ", ".join(memberships))])

    extras = []
    licence = _clean(cv.get("drivers_licence"))
    if licence:
        extras.append(_block("body", f"Driver's licence: {licence}"))
    authorisation = _clean(cv.get("work_authorization"))
    if authorisation:
        extras.append(_block("body", f"Work authorisation: {authorisation}"))
    add_section("additional", extras)
    return blocks


class _Bar(Flowable):
    """A navy or gold rule. It is a drawing, not text, so extractors skip it."""

    def __init__(self, color, thickness: float, width=None, space_before=0, space_after=0):
        super().__init__()
        self.color = color
        self.thickness = thickness
        self._fixed = width
        self.spaceBefore = space_before
        self.spaceAfter = space_after

    def wrap(self, avail_width, _avail_height):
        self._bar = min(self._fixed, avail_width) if self._fixed else avail_width
        self.width = avail_width
        self.height = self.thickness
        return avail_width, self.thickness

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self._bar, self.thickness, stroke=0, fill=1)


class _DatedLine(Flowable):
    """Role or qualification on the left, date on the right, both real text.

    The left paragraph is drawn first and the date second, on the same
    baseline, so a text extractor reads the role and then the date.
    """

    def __init__(self, left_html: str, right: str, left_style: ParagraphStyle,
                 right_font: str, right_size: float, right_color, space_before=0, space_after=1):
        super().__init__()
        self.left_html = left_html
        self.right = right or ""
        self.left_style = left_style
        self.right_font = right_font
        self.right_size = right_size
        self.right_color = right_color
        self.spaceBefore = space_before
        self.spaceAfter = space_after

    def wrap(self, avail_width, avail_height):
        gap = 12 if self.right else 0
        self._right_w = stringWidth(self.right, self.right_font, self.right_size) + gap if self.right else 0
        left_width = max(avail_width * 0.45, avail_width - self._right_w)
        if left_width + self._right_w > avail_width:
            left_width = max(40, avail_width - self._right_w)
        self._left = Paragraph(self.left_html, self.left_style)
        _, left_h = self._left.wrap(left_width, avail_height)
        self.width = avail_width
        self.height = max(left_h, self.right_size + 1)
        self._left_h = left_h
        return avail_width, self.height

    def draw(self):
        self._left.drawOn(self.canv, 0, self.height - self._left_h)
        if not self.right:
            return
        self.canv.setFillColor(self.right_color)
        self.canv.setFont(self.right_font, self.right_size)
        # First-line baseline. Paragraph height is leading × lines; the
        # baseline sits one leading below the top, plus the font's descent.
        baseline = self.height - self.left_style.leading + 1
        self.canv.drawRightString(self.width, baseline, self.right)


class _SolidParagraph(Paragraph):
    """Keep a bullet on one page when the whole bullet fits on a page."""

    def split(self, avail_width, avail_height):
        _, height = Paragraph.wrap(self, avail_width, avail_height)
        frame = getattr(self, "_frame", None)
        frame_height = getattr(frame, "_aH", 700) if frame is not None else 700
        if height <= frame_height + 1:
            return []
        return Paragraph.split(self, avail_width, avail_height)


def _pdf_styles(style: dict) -> dict[str, ParagraphStyle]:
    font, bold, italic = style["pdf_font"], style["pdf_bold"], style["pdf_italic"]
    common = dict(fontName=font, alignment=TA_LEFT, textColor=INK)
    return {
        "name": ParagraphStyle(
            "CVName", fontName=bold, fontSize=style["name_size"], leading=style["name_leading"],
            textColor=NAVY, alignment=TA_LEFT, spaceBefore=0, spaceAfter=1,
        ),
        "sub": ParagraphStyle(
            "CVSub", fontName=bold, fontSize=style["sub_size"], leading=style["sub_leading"],
            textColor=NAVY, spaceBefore=1, spaceAfter=2,
        ),
        "contact": ParagraphStyle(
            "CVContact", fontName=font, alignment=TA_LEFT, textColor=MUTED,
            fontSize=style["contact_size"], leading=style["contact_leading"],
            spaceBefore=0, spaceAfter=1,
        ),
        "heading": ParagraphStyle(
            "CVHeading", fontName=bold, fontSize=style["section_size"], leading=style["section_leading"],
            textColor=NAVY, spaceBefore=0, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "CVBody", **common, fontSize=style["body_size"], leading=style["body_leading"],
            spaceBefore=0, spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "CVMeta", fontName=italic, fontSize=style["meta_size"], leading=style["meta_leading"],
            textColor=MUTED, spaceBefore=1, spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "CVBullet", **common, fontSize=style["bullet_size"], leading=style["bullet_leading"],
            leftIndent=14, firstLineIndent=-12, spaceBefore=style["bullet_space"],
            spaceAfter=style["bullet_space"],
        ),
        "label": ParagraphStyle(
            "CVLabel", fontName=bold, fontSize=style["body_size"], leading=style["body_leading"],
            textColor=NAVY, spaceBefore=4, spaceAfter=1,
        ),
        "role": ParagraphStyle(
            "CVRole", fontName=font, fontSize=style["role_size"], leading=style["role_leading"],
            textColor=INK, spaceBefore=0, spaceAfter=0,
        ),
    }


def _header_bar(variant: str, style: dict) -> _Bar:
    if variant == "full":
        return _Bar(GOLD, 3.25, space_before=0, space_after=10)
    if variant == "short":
        return _Bar(GOLD, 2.6, width=78, space_before=2, space_after=7)
    if variant == "hairline":
        return _Bar(GOLD, 0.9, space_before=5, space_after=2)
    return _Bar(NAVY, 1.0, space_before=6, space_after=1)


def _section_bar(variant: str, style: dict) -> _Bar:
    if variant == "short":
        return _Bar(GOLD, 2.2, width=78, space_before=0, space_after=style["rule_gap"])
    if variant == "hairline":
        return _Bar(GOLD, 0.6, space_before=0, space_after=style["rule_gap"])
    return _Bar(NAVY, 0.75, space_before=0, space_after=style["rule_gap"])


def _left_html(bold: str, rest: str) -> str:
    parts = []
    if bold:
        parts.append(f"<b>{escape(bold)}</b>")
    if rest:
        parts.append(f"<font color='#3D4754'>{escape(rest)}</font>")
    if bold and rest:
        return "  —  ".join(parts)
    return "".join(parts) or ""


def render_cv_pdf(cv: dict, template: str | None = None) -> bytes:
    cv = _xml_safe(cv)
    style = template_style(template)
    blocks = cv_blocks(cv, template)
    styles = _pdf_styles(style)
    story = []
    for block in blocks:
        kind = block["kind"]
        if kind == "bar":
            if block["variant"] == "section":
                flow = _section_bar(style["section_rule"], style)
            else:
                flow = _header_bar(block["variant"], style)
            flow.keepWithNext = bool(block["keep"])
            story.append(flow)
            continue
        if kind == "heading":
            flow = Paragraph(escape(block["text"]), styles["heading"])
            flow.spaceBefore = block["space_before"]
            flow.keepWithNext = True
            story.append(flow)
            continue
        if kind == "name":
            flow = Paragraph(escape(block["text"]), styles["name"])
        elif kind == "subhead":
            flow = Paragraph(escape(block["text"]), styles["sub"])
        elif kind == "contact":
            flow = Paragraph(escape(block["text"]), styles["contact"])
        elif kind == "body":
            flow = _SolidParagraph(escape(block["text"]), styles["body"])
        elif kind == "meta":
            flow = Paragraph(escape(block["text"]), styles["meta"])
        elif kind == "label":
            flow = Paragraph(escape(block["text"]), styles["label"])
        elif kind == "bullet":
            flow = _SolidParagraph("•  " + escape(block["text"]), styles["bullet"])
        elif kind == "dated":
            flow = _DatedLine(
                _left_html(block.get("left_bold") or "", block.get("left_rest") or ""),
                block.get("right") or "",
                styles["role"],
                style["pdf_font"],
                style["meta_size"],
                MUTED,
                space_before=block["space_before"],
                space_after=1,
            )
        else:
            continue
        flow.keepWithNext = bool(block["keep"])
        story.append(flow)

    if not story:
        story.append(Paragraph("Curriculum Vitae", styles["name"]))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=style["margin"], rightMargin=style["margin"],
        topMargin=style["top"], bottomMargin=style["bottom"],
        title=_clean(cv.get("full_name")) or "Curriculum Vitae",
        author=_clean(cv.get("full_name")),
    )
    doc.build(story)
    return buf.getvalue()


# ---- DOCX (python-docx) -----------------------------------------------------

def _rgb(color):
    from docx.shared import RGBColor
    return RGBColor(int(round(color.red * 255)), int(round(color.green * 255)), int(round(color.blue * 255)))


def _set_run_font(run, name: str, size, bold=False, italic=False, color=None):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    run.bold = bold
    run.italic = italic
    run.font.name = name
    run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        r_fonts.set(qn(attr), name)


def _border(paragraph, edge: str, color, size: str, right_indent=None):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    if right_indent is not None:
        paragraph.paragraph_format.right_indent = right_indent
    hex_color = "%02x%02x%02x" % (
        int(round(color.red * 255)), int(round(color.green * 255)), int(round(color.blue * 255)),
    )
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    edge_el = OxmlElement(f"w:{edge}")
    edge_el.set(qn("w:val"), "single")
    edge_el.set(qn("w:sz"), size)
    edge_el.set(qn("w:space"), "1")
    edge_el.set(qn("w:color"), hex_color)
    p_bdr.append(edge_el)


def _tighten(paragraph, before=0, after=0, exact=None, keep=False, together=True):
    from docx.enum.text import WD_LINE_SPACING
    from docx.shared import Pt

    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.widow_control = True
    fmt.keep_together = together
    fmt.keep_with_next = keep
    if exact:
        fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        fmt.line_spacing = Pt(exact)


def _rule_paragraph(document, style: dict, variant: str, content_width):
    from docx.shared import Cm, Pt

    paragraph = document.add_paragraph()
    thickness = {"full": "18", "short": "16", "hairline": "8", "close": "8"}.get(variant, "8")
    color = NAVY if variant == "close" else GOLD
    if variant in {"full", "short", "hairline"} and variant != "close":
        color = GOLD
    right = None
    if variant == "short":
        right = content_width - Cm(2.8) if content_width > Cm(4) else None
    _border(paragraph, "bottom", color, thickness, right_indent=right)
    after = 8 if variant in {"full", "short"} else (4 if variant == "close" else 2)
    before = 2 if variant == "short" else (6 if variant == "close" else 0)
    _tighten(paragraph, before=before, after=after, exact=4, keep=variant not in {"close"})
    paragraph.paragraph_format.space_after = Pt(after)
    return paragraph


def _section_rule_paragraph(document, style: dict, content_width, keep: bool):
    from docx.shared import Cm, Pt

    variant = style["section_rule"]
    paragraph = document.add_paragraph()
    if variant == "short":
        color, size, right = GOLD, "14", (content_width - Cm(2.8) if content_width > Cm(4) else None)
    elif variant == "hairline":
        color, size, right = GOLD, "6", None
    else:
        color, size, right = NAVY, "8", None
    _border(paragraph, "bottom", color, size, right_indent=right)
    _tighten(paragraph, before=0, after=style["rule_gap"], exact=3, keep=keep)
    paragraph.paragraph_format.space_after = Pt(style["rule_gap"])
    return paragraph


def render_cv_docx(cv: dict, template: str | None = None) -> bytes:
    cv = _xml_safe(cv)
    from docx import Document
    from docx.enum.text import WD_TAB_ALIGNMENT
    from docx.shared import Mm, Pt

    style = template_style(template)
    font = style["docx_font"]
    navy, muted, ink = _rgb(NAVY), _rgb(MUTED), _rgb(INK)
    blocks = cv_blocks(cv, template)

    document = Document()
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Pt(style["margin"])
    section.right_margin = Pt(style["margin"])
    section.top_margin = Pt(style["top"])
    section.bottom_margin = Pt(style["bottom"])
    content_width = section.page_width - section.left_margin - section.right_margin

    normal = document.styles["Normal"]
    normal.font.name = font
    normal.font.size = Pt(style["body_size"])
    normal.font.color.rgb = ink
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    r_pr = normal.element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        r_fonts.set(qn(attr), font)

    seen_heading = False
    for block in blocks:
        kind = block["kind"]
        keep = bool(block["keep"])
        if kind == "bar":
            variant = block["variant"]
            if not seen_heading and variant in {"full", "short", "hairline", "close"}:
                _rule_paragraph(document, style, variant, content_width)
            else:
                _section_rule_paragraph(document, style, content_width, keep)
            continue
        paragraph = document.add_paragraph()
        if kind == "name":
            _tighten(paragraph, before=2, after=0, exact=style["name_leading"], keep=keep)
            _set_run_font(paragraph.add_run(block["text"]), font, style["name_size"], bold=True, color=navy)
        elif kind == "subhead":
            _tighten(paragraph, before=1, after=1, exact=style["sub_leading"], keep=keep)
            _set_run_font(paragraph.add_run(block["text"]), font, style["sub_size"], bold=True, color=navy)
        elif kind == "contact":
            _tighten(paragraph, before=0, after=0, exact=style["contact_leading"], keep=keep)
            _set_run_font(paragraph.add_run(block["text"]), font, style["contact_size"], color=muted)
        elif kind == "heading":
            seen_heading = True
            _tighten(paragraph, before=block["space_before"], after=1, exact=style["section_leading"], keep=True)
            _set_run_font(paragraph.add_run(block["text"]), font, style["section_size"], bold=True, color=navy)
        elif kind == "body":
            _tighten(paragraph, before=1, after=1, exact=style["body_leading"], keep=keep)
            _set_run_font(paragraph.add_run(block["text"]), font, style["body_size"], color=ink)
        elif kind == "meta":
            _tighten(paragraph, before=0, after=1, exact=style["meta_leading"], keep=keep)
            _set_run_font(paragraph.add_run(block["text"]), font, style["meta_size"], italic=True, color=muted)
        elif kind == "label":
            _tighten(paragraph, before=3, after=0, exact=style["body_leading"], keep=True)
            _set_run_font(paragraph.add_run(block["text"]), font, style["body_size"], bold=True, color=navy)
        elif kind == "bullet":
            _tighten(paragraph, before=style["bullet_space"], after=style["bullet_space"],
                     exact=style["bullet_leading"], keep=False, together=True)
            paragraph.paragraph_format.left_indent = Pt(14)
            paragraph.paragraph_format.first_line_indent = Pt(-12)
            _set_run_font(paragraph.add_run("•  " + block["text"]), font, style["bullet_size"], color=ink)
        elif kind == "dated":
            left_bold = block.get("left_bold") or ""
            left_rest = block.get("left_rest") or ""
            right = block.get("right") or ""
            left_plain = " — ".join(part for part in (left_bold, left_rest) if part)
            # A right-aligned tab keeps the date on the same line when it fits.
            # A very long title drops the date onto the next line instead of colliding.
            approx = len(left_plain) * style["role_size"] * 0.5 + len(right) * style["meta_size"] * 0.52
            use_tab = bool(right) and approx < (content_width / 12700) - 18
            _tighten(paragraph, before=block["space_before"], after=0, exact=style["role_leading"], keep=keep)
            if use_tab:
                paragraph.paragraph_format.tab_stops.add_tab_stop(content_width, WD_TAB_ALIGNMENT.RIGHT)
            if left_bold:
                _set_run_font(paragraph.add_run(left_bold), font, style["role_size"], bold=True, color=ink)
            if left_rest:
                prefix = " — " if left_bold else ""
                _set_run_font(paragraph.add_run(prefix + left_rest), font, style["role_size"], color=muted)
            if use_tab:
                _set_run_font(paragraph.add_run("\t" + right), font, style["meta_size"], color=muted)
            elif right and not left_plain:
                _set_run_font(paragraph.add_run(right), font, style["meta_size"], color=muted)
            elif right:
                # Date follows on its own line so a long title stays readable.
                date_p = document.add_paragraph()
                _tighten(date_p, before=0, after=0, exact=style["meta_leading"], keep=keep)
                _set_run_font(date_p.add_run(right), font, style["meta_size"], color=muted)
        else:
            continue

    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


# ---- Cover letter -----------------------------------------------------------

def render_letter_pdf(text: str) -> bytes:
    text = _xml_safe(text)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=2 * 28.35, bottomMargin=2 * 28.35,
        leftMargin=2.2 * 28.35, rightMargin=2.2 * 28.35, title="Cover Letter",
    )
    body = ParagraphStyle("LetterBody", fontName="Helvetica", fontSize=11, leading=16, spaceAfter=8, textColor=INK)
    story = []
    for para in (text or "").split("\n\n"):
        story.append(Paragraph(escape(para).replace("\n", "<br/>"), body))
    if not story:
        story.append(Paragraph("", body))
    doc.build(story)
    return buf.getvalue()


def render_letter_docx(text: str) -> bytes:
    text = _xml_safe(text)
    from docx import Document
    from docx.shared import Pt
    document = Document()
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(11)
    for para in (text or "").split("\n\n"):
        document.add_paragraph(para)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
