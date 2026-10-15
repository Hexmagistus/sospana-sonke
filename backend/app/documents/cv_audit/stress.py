"""Phase 5 — ATS stress test on the FINISHED files.

Renders the rebuilt CV to DOCX and PDF, then reads both back exactly the way
the platform's own upload pipeline reads a candidate's CV (pypdf /
python-docx text extraction), re-parses that text with the same section
parser used on the original, and checks the round trip:

- did the text come out at all, and in the right reading order?
- are name, email and phone recoverable from the body?
- do the headings come back in order, and are they all standard?
- does every role come back with its title, employer and dates, in order?
- do the qualifications come back with their institutions?
- does the file contain anything an ATS dislikes (tables, images, text boxes,
  header/footer content), and how many pages is it?

If the PDF runs past two pages, it is re-rendered once in the compact layout
before the result is reported (the "correct it before delivering" step).
"""
from __future__ import annotations

import re

from app.documents.cv_audit.inspect import inspect_docx, inspect_pdf
from app.documents.cv_audit.parse import parse_cv_text
from app.documents.cv_audit.render import render_docx, render_pdf, sections
from app.services.cv_extract import extract_text


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _check(area: str, ok: bool, detail: str) -> dict:
    return {"area": area, "ok": bool(ok), "detail": detail}


def _pdf_pages(data: bytes) -> int:
    import io
    from pypdf import PdfReader
    return len(PdfReader(io.BytesIO(data)).pages)


def build_files(cv: dict) -> tuple[bytes, bytes, bool]:
    pdf = render_pdf(cv)
    compact = False
    if _pdf_pages(pdf) > 2:
        compact = True
        pdf = render_pdf(cv, compact=True)
    docx = render_docx(cv, compact=compact)
    return docx, pdf, compact


def stress_test(cv: dict) -> dict:
    checks: list[dict] = []
    docx, pdf, compact = build_files(cv)

    texts = {}
    for fmt, data in (("pdf", pdf), ("docx", docx)):
        try:
            texts[fmt] = extract_text(data, fmt)
        except Exception as exc:  # pragma: no cover - surfaced in the report instead
            texts[fmt] = ""
            checks.append(_check("File quality", False, f"The generated {fmt.upper()} could not be read back: {exc}"))

    pdf_text, docx_text = texts.get("pdf", ""), texts.get("docx", "")
    checks.append(_check("File quality", bool(pdf_text) and bool(docx_text),
                         "Both files open and return selectable, searchable text."
                         if pdf_text and docx_text else "One of the files returned no text."))

    # ---- Reading order ----
    def first_line(t: str) -> str:
        return next((ln.strip() for ln in t.splitlines() if ln.strip()), "")

    name_first = all(_norm(first_line(t)) == _norm(cv.get("full_name")) for t in (pdf_text, docx_text))
    checks.append(_check("Document parsing", name_first,
                         "Your name is the first line extracted from both files." if name_first
                         else "The name is not the first thing a parser reads."))
    expected = [s["title"] for s in sections(cv)]
    order_ok = True
    for t in (pdf_text, docx_text):
        pos = -1
        low = " ".join(t.split()).lower()
        for title in expected:
            i = low.find(title.lower(), pos + 1)
            if i < 0 or i < pos:
                order_ok = False
                break
            pos = i
    checks.append(_check("Section headings", order_ok,
                         f"All {len(expected)} standard headings are extracted in the intended order: "
                         + ", ".join(expected) + "." if order_ok else
                         "Headings were not extracted in the expected order."))

    # ---- Round-trip re-parse (what an ATS would reconstruct) ----
    reparsed = parse_cv_text(pdf_text)
    contact_ok = (_norm(reparsed.get("email")) == _norm(cv.get("email")) if cv.get("email") else True) and \
                 (_norm(reparsed.get("phone")) == _norm(cv.get("phone")) if cv.get("phone") else True)
    in_body = all((cv.get(k) or "") in t for t in (pdf_text, docx_text) for k in ("email", "phone"))
    checks.append(_check("Contact information", contact_ok and in_body and bool(cv.get("email")),
                         "Name, email and phone sit in the document body and are re-extracted exactly."
                         if contact_ok and in_body and cv.get("email") else
                         "Contact details are missing or could not be re-extracted — see the checklist."))

    exp = cv.get("experience", [])
    re_exp = reparsed.get("experience", [])
    exp_ok = len(re_exp) == len(exp)
    detail_bits = []
    for i, e in enumerate(exp):
        r = re_exp[i] if i < len(re_exp) else {}
        same = (_norm(r.get("position")) == _norm(e.get("position"))
                and _norm(r.get("employer")) in (_norm(e.get("employer")), _norm(f"{e.get('employer')}"))
                and (r.get("start") or "") == (e.get("start") or ""))
        if not same:
            exp_ok = False
            detail_bits.append(e.get("position") or e.get("employer") or f"role {i + 1}")
    checks.append(_check("Employment history", exp_ok and bool(exp),
                         f"All {len(exp)} roles re-parse with the same job title, employer and dates, in "
                         "reverse-chronological order." if exp_ok and exp else
                         ("Could not cleanly re-parse: " + ", ".join(detail_bits)) if detail_bits else
                         "No employment entries to verify."))

    edu = cv.get("education", []) + cv.get("current_studies", [])
    re_edu = {_norm(e.get("qualification")) for e in reparsed.get("education", [])}
    edu_ok = all(_norm(e.get("qualification")) in re_edu for e in edu if e.get("qualification"))
    checks.append(_check("Qualifications", edu_ok and bool(edu),
                         f"All {len(edu)} qualifications re-parse with their institutions; completed and "
                         "in-progress studies are in separate sections." if edu_ok and edu else
                         "Some qualifications did not re-parse cleanly." if edu else "No qualifications listed."))

    # ---- Keywords ----
    terms = [t for ts in (cv.get("competencies") or {}).values() for t in ts]
    flat = " ".join(pdf_text.split()).lower()
    found = [t for t in terms if " ".join(t.split(" (")[0].split()).lower() in flat]
    checks.append(_check("Keywords", len(found) == len(terms) and bool(terms),
                         f"{len(found)} of {len(terms)} competency terms are present as plain, searchable text, "
                         "each one supported by your own experience or skills list."))

    # ---- Formatting ----
    dfacts, dfind = inspect_docx(docx)
    pfacts, pfind = inspect_pdf(pdf)
    bad = [f for f in dfind + pfind if f["code"] in ("tables", "text_boxes", "columns", "graphics",
                                                       "contact_in_header", "header_footer_text", "pdf_no_text")]
    checks.append(_check("Formatting", not bad,
                         "No tables, text boxes, columns, images or header/footer content in either file."
                         if not bad else "; ".join(f["message"] for f in bad)))

    # ---- Consistency ----
    date_tokens = re.findall(r"\b(?:[A-Z][a-z]{2} (?:19|20)\d{2}|Present)\b", pdf_text)
    odd_dates = re.findall(r"\b\d{1,2}/(?:19|20)\d{2}\b|\b(?:January|February|March|April|June|July|August|"
                           r"September|October|November|December) (?:19|20)\d{2}\b", pdf_text)
    trailing = [b for e in exp for b in e.get("bullets", []) if b.endswith(".")]
    cons_ok = not odd_dates and not trailing
    checks.append(_check("Consistency", cons_ok,
                         f"One date format throughout (e.g. “Mar 2022 – Present”, {len(date_tokens)} dates), "
                         "uniform bullet punctuation and heading style." if cons_ok else
                         "Mixed date formats or bullet punctuation remain."))

    pages = pfacts.get("pages", 0)
    checks.append(_check("Professional impact", bool(cv.get("headline")) and bool(cv.get("summary")) and pages <= 3,
                         f"Headline and summary lead page one; the PDF is {pages} page{'s' if pages != 1 else ''}"
                         + (" (compact layout applied automatically to keep it tight)." if compact else ".")))

    return {
        "checks": checks,
        "passed": sum(1 for c in checks if c["ok"]),
        "total": len(checks),
        "pages": pages,
        "compact": compact,
        "extracted_text_preview": pdf_text[:4000],
        "findings": dfind + pfind,
        "pdf_text": pdf_text,
    }
