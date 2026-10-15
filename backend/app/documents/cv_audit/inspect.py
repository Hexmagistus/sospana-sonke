"""Phase 1a — inspect the ORIGINAL uploaded file for ATS parsing risks.

Looks at the document's real structure (not just its extracted text): tables,
text boxes, multi-column sections, header/footer content, images, number of
fonts, page count, and whether a PDF actually carries selectable text. Each
finding is a dict {code, severity, area, message, impact} so the UI and the
report can render it without re-deriving anything.

Severity: "high" (likely to break parsing), "medium" (may degrade parsing or
recruiter impression), "low" (polish).
"""
from __future__ import annotations

import io
import re
import zipfile

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _finding(code: str, severity: str, area: str, message: str, impact: str) -> dict:
    return {"code": code, "severity": severity, "area": area, "message": message, "impact": impact}


def inspect_docx(data: bytes) -> tuple[dict, list[dict]]:
    facts: dict = {"format": "docx"}
    findings: list[dict] = []
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        findings.append(_finding("docx_corrupt", "high", "ats",
                                 "The Word file could not be opened as a valid DOCX package.",
                                 "Most ATS platforms will reject or mis-read a corrupt file."))
        return facts, findings

    names = z.namelist()
    body = z.read("word/document.xml").decode("utf8", "ignore") if "word/document.xml" in names else ""

    tables = body.count("<w:tbl>") + body.count("<w:tbl ")
    textboxes = body.count("<w:txbxContent")
    images = len([n for n in names if n.startswith("word/media/")])
    drawings = body.count("<w:drawing")
    cols = [int(c) for c in re.findall(r'<w:cols[^>]*w:num="(\d+)"', body)]
    multi_col = any(c > 1 for c in cols)
    fonts = set(re.findall(r'w:ascii="([^"]+)"', body))

    header_text = ""
    footer_text = ""
    for n in names:
        if re.match(r"word/header\d*\.xml$", n):
            header_text += " " + re.sub(r"<[^>]+>", " ", z.read(n).decode("utf8", "ignore"))
        if re.match(r"word/footer\d*\.xml$", n):
            footer_text += " " + re.sub(r"<[^>]+>", " ", z.read(n).decode("utf8", "ignore"))
    header_text = " ".join(header_text.split())
    footer_text = " ".join(footer_text.split())
    hf = f"{header_text} {footer_text}"

    facts.update({"tables": tables, "text_boxes": textboxes, "images": images,
                  "multi_column": multi_col, "font_count": len(fonts), "fonts": sorted(fonts)[:8],
                  "header_footer_chars": len(hf.strip())})

    if tables:
        findings.append(_finding(
            "tables", "high" if tables > 1 else "medium", "ats",
            f"The document uses {tables} table{'s' if tables != 1 else ''} for layout.",
            "Many ATS parsers read table cells out of order or skip them, which can scramble "
            "job titles, dates and employers."))
    if textboxes:
        findings.append(_finding(
            "text_boxes", "high", "ats",
            f"{textboxes} text box{'es' if textboxes != 1 else ''} found.",
            "Text inside text boxes is frequently ignored entirely by ATS software."))
    if multi_col:
        findings.append(_finding(
            "columns", "high", "ats", "A multi-column section layout is used.",
            "Columns are often read straight across the page, mixing unrelated lines together."))
    if images or drawings:
        findings.append(_finding(
            "graphics", "medium", "ats",
            "The document contains images, icons or graphics (possibly a photo, logo, or skill bars).",
            "Graphics carry no readable text for an ATS; a photograph can also introduce bias "
            "and is not expected on South African or international professional CVs."))
    if re.search(r"@|\+?\d[\d\s]{7,}", hf):
        findings.append(_finding(
            "contact_in_header", "high", "ats",
            "Contact details appear in the page header or footer.",
            "Several ATS platforms skip headers and footers, so your email or phone may not be captured."))
    elif len(hf.strip()) > 3:
        findings.append(_finding(
            "header_footer_text", "low", "ats", "Text is placed in the page header or footer.",
            "Header/footer text can be skipped by parsers — keep essential content in the body."))
    if len(fonts) > 3:
        findings.append(_finding(
            "many_fonts", "low", "presentation",
            f"{len(fonts)} different fonts are used.",
            "Mixed typography looks inconsistent to recruiters."))
    return facts, findings


def inspect_pdf(data: bytes) -> tuple[dict, list[dict]]:
    facts: dict = {"format": "pdf"}
    findings: list[dict] = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        findings.append(_finding("pdf_corrupt", "high", "ats", "The PDF could not be opened.",
                                 "An unreadable PDF will be rejected by most portals."))
        return facts, findings

    pages = len(reader.pages)
    images = 0
    text_chars = 0
    for page in reader.pages:
        try:
            images += len(page.images)
        except Exception:
            pass
        text_chars += len((page.extract_text() or "").strip())
    facts.update({"pages": pages, "images": images, "text_chars": text_chars})

    if text_chars < 200:
        findings.append(_finding(
            "pdf_no_text", "high", "ats", "The PDF has little or no selectable text — it is probably a scanned image.",
            "An ATS cannot read an image of a CV; the application may be scored as empty."))
    if images:
        findings.append(_finding(
            "graphics", "medium", "ats",
            f"The PDF contains {images} embedded image{'s' if images != 1 else ''} (photo, logo, icons or skill bars).",
            "Images carry no readable text; a photograph is not expected on a professional CV."))
    if pages > 3:
        findings.append(_finding(
            "too_long", "medium", "presentation", f"The CV runs to {pages} pages.",
            "Recruiters typically spend under a minute on a first scan — 2 pages (3 at most "
            "for long technical careers) is the norm."))
    return facts, findings


def inspect_text_layout(text: str) -> list[dict]:
    """Signals visible in extracted text that suggest column/table interleaving."""
    findings: list[dict] = []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return findings
    # Lines with big internal gaps usually come from side-by-side columns.
    gappy = sum(1 for ln in lines if re.search(r"\S\s{6,}\S", ln))
    if gappy >= max(3, len(lines) // 8):
        findings.append(_finding(
            "interleaved_text", "medium", "ats",
            "The extracted text shows side-by-side content on the same lines.",
            "This usually means a two-column or tabbed layout that parsers read across, mixing sections."))
    decorative = sum(1 for ln in lines if re.match(r"^[\s★☆●○◆◇■□▪▫✓✔➢➤►▶✦✧❖]+\S", ln))
    stars = len(re.findall(r"[★☆]{2,}|[●○]{3,}", text))
    if stars:
        findings.append(_finding(
            "rating_symbols", "medium", "presentation",
            "Skill-rating symbols (stars or dots) are used.",
            "Ratings are subjective, unreadable to an ATS, and invite the question “why only 3 out of 5?”."))
    elif decorative > 5:
        findings.append(_finding(
            "decorative_bullets", "low", "ats", "Decorative bullet symbols are used throughout.",
            "Unusual symbols can extract as garbage characters — plain round bullets are safest."))
    return findings


def inspect_document(data: bytes, extension: str, text: str) -> tuple[dict, list[dict]]:
    ext = (extension or "").lower()
    if ext == "docx":
        facts, findings = inspect_docx(data)
    elif ext == "pdf":
        facts, findings = inspect_pdf(data)
    else:
        facts, findings = {"format": ext or "txt"}, []
        findings.append(_finding(
            "plain_text_source", "low", "presentation", "The CV was supplied as plain text.",
            "Plain text parses well but cannot be submitted as a polished document — the rebuilt "
            "DOCX/PDF fixes this."))
    findings += inspect_text_layout(text)
    return facts, findings
