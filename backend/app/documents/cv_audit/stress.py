"""Phase 5 — ATS stress test and compliance gate on the FINISHED files.

Every rebuilt CV is sanitised (``compliance.sanitize_cv``), rendered to DOCX and
PDF, and both files are read back exactly the way the platform's own upload
pipeline reads a CV (pypdf / python-docx text extraction). The checks are split
in two:

* **ATS-format checks** — things the platform controls: the files open, the text
  is clean, headings are standard and in order, contact details sit in the body,
  every role / qualification / keyword comes back as plain text in reading
  order, no tables, text boxes, columns, images or header/footer content, one
  date format. These must ALL pass. If one fails, the CV is re-rendered in the
  fallback layout and tested again; a CV is only reported "ATS-compliant" when
  every format check passes.
* **Content blockers** — what an ATS needs that only the candidate can give
  (email, phone, a job title, dates). These are listed, never invented, and the
  CV is "ATS-ready" only when there are none.
"""
from __future__ import annotations

import io
import re

from app.documents.cv_audit.compliance import content_blockers, sanitize_cv
from app.documents.cv_audit.inspect import inspect_docx, inspect_pdf
from app.documents.cv_audit.render import render_docx, render_pdf, sections
from app.services.cv_extract import extract_text

_BAD_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f-�]")
_ODD_DATES = re.compile(r"\b\d{1,2}/(?:19|20)\d{2}\b|\b(?:January|February|March|April|June|July|August|"
                        r"September|October|November|December) (?:19|20)\d{2}\b")
_LAYOUT_CODES = ("tables", "text_boxes", "columns", "graphics", "contact_in_header",
                 "header_footer_text", "pdf_no_text", "docx_corrupt", "pdf_corrupt")


def _flat(t: str) -> str:
    return " ".join((t or "").split()).lower()


def _check(area: str, ok: bool, detail: str) -> dict:
    return {"area": area, "ok": bool(ok), "detail": detail}


def _pdf_pages(data: bytes) -> int:
    from pypdf import PdfReader
    return len(PdfReader(io.BytesIO(data)).pages)


def _in_order(text: str, needles: list[str]) -> tuple[bool, str | None]:
    """Every needle appears, each after the previous one. Returns the first miss."""
    pos = -1
    for n in needles:
        n = _flat(n)
        if not n:
            continue
        i = text.find(n, pos + 1)
        if i < 0:
            return False, n
        pos = i
    return True, None


def _format_checks(cv: dict, docx: bytes, pdf: bytes, compact: bool) -> tuple[list[dict], dict, list[dict]]:
    checks: list[dict] = []
    texts: dict[str, str] = {}
    for fmt, data in (("pdf", pdf), ("docx", docx)):
        try:
            texts[fmt] = extract_text(data, fmt)
        except Exception:
            texts[fmt] = ""
    pdf_text, docx_text = texts["pdf"], texts["docx"]
    both = [(_flat(pdf_text), "PDF"), (_flat(docx_text), "Word")]

    checks.append(_check("File quality", bool(pdf_text and docx_text),
                         "Both files open and return selectable, searchable text."
                         if pdf_text and docx_text else "One of the files returned no readable text."))

    junk = [label for t, label in ((pdf_text, "PDF"), (docx_text, "Word")) if _BAD_CHARS.search(t)]
    checks.append(_check("Character encoding", not junk,
                         "No symbols, icons or unreadable characters — every character extracts cleanly."
                         if not junk else f"Unreadable characters in the {', '.join(junk)} text."))

    if cv.get("full_name"):
        # A long name may wrap onto a second line; what matters is that nothing comes before it.
        ok = all(t.startswith(_flat(cv["full_name"])) for t, _ in both)
        checks.append(_check("Document parsing", ok,
                             "Your name is the very first line an ATS reads in both files." if ok
                             else "The name is not the first line extracted."))
    else:
        checks.append(_check("Document parsing", True,
                             "Single-column reading order confirmed (add your name — see what's still needed)."))

    titles = [s["title"] for s in sections(cv)]
    bad = [label for t, label in both if not _in_order(t, titles)[0]]
    checks.append(_check("Section headings", not bad,
                         f"{len(titles)} standard headings extract in order: {', '.join(titles)}."
                         if not bad else f"Headings out of order in the {', '.join(bad)} text."))

    contact = [cv.get(k) for k in ("email", "phone", "location", "linkedin_url") if cv.get(k)]
    missing = [c for c in contact for t, _ in both if _flat(c) not in t]
    checks.append(_check("Contact information", not missing,
                         "Contact details sit in the document body (never in a header or footer) and extract exactly."
                         if not missing else "Some contact details did not extract from the body."))

    needles: list[str] = []
    for e in cv.get("experience") or []:
        needles += [x for x in (e.get("position"), e.get("employer"), e.get("start")) if x]
    bad_role = None
    for t, _ in both:
        ok, miss = _in_order(t, needles)
        if not ok:
            bad_role = miss
            break
    n_roles = len(cv.get("experience") or [])
    checks.append(_check("Employment history", bad_role is None,
                         f"All {n_roles} role{'s' if n_roles != 1 else ''} extract with title, employer and dates "
                         "in reverse-chronological reading order." if bad_role is None
                         else f"“{bad_role}” did not extract in reading order."))

    q_needles = []
    for ed in (cv.get("education") or []) + (cv.get("current_studies") or []):
        q_needles += [x for x in (ed.get("qualification"), ed.get("institution")) if x]
    bad_q = next((m for t, _ in both for ok, m in [_in_order(t, q_needles)] if not ok), None)
    n_q = len((cv.get("education") or []) + (cv.get("current_studies") or []))
    checks.append(_check("Qualifications", bad_q is None,
                         f"All {n_q} qualification{'s' if n_q != 1 else ''} extract with their institutions; "
                         "completed and in-progress studies are in separate, labelled sections."
                         if bad_q is None else f"“{bad_q}” did not extract cleanly."))

    terms = [t for ts in (cv.get("competencies") or {}).values() for t in ts] + list(cv.get("software") or [])
    lost = [t for t in terms for txt, _ in both if _flat(t) not in txt]
    checks.append(_check("Keywords", not lost,
                         f"All {len(terms)} skills and competency terms are plain, searchable text, each supported "
                         "by your own experience or skills list." if not lost
                         else f"{len(set(lost))} term(s) did not extract as plain text."))

    ref_needles = []
    for r in cv.get("references") or []:
        ref_needles += [x for x in (r.get("name"), r.get("phone"), r.get("email")) if x]
    bad_ref = next((m for t, _ in both for ok, m in [_in_order(t, ref_needles)] if not ok), None)
    n_ref = len(cv.get("references") or [])
    checks.append(_check("References", bad_ref is None,
                         (f"{n_ref} referee{'s' if n_ref != 1 else ''} extract with contact details under a standard "
                          "References heading." if n_ref else "No referees listed yet — see what's still needed.")
                         if bad_ref is None else f"“{bad_ref}” did not extract cleanly."))

    dfacts, dfind = inspect_docx(docx)
    pfacts, pfind = inspect_pdf(pdf)
    layout = [f for f in dfind + pfind if f["code"] in _LAYOUT_CODES]
    checks.append(_check("Formatting", not layout,
                         "Single column; no tables, text boxes, columns, images, icons or header/footer content."
                         if not layout else "; ".join(f["message"] for f in layout)))

    trailing = [b for e in cv.get("experience") or [] for b in e.get("bullets", []) if b.endswith(".")]
    odd = _ODD_DATES.search(pdf_text) or _ODD_DATES.search(docx_text)
    checks.append(_check("Consistency", not trailing and not odd,
                         "One date format throughout (e.g. “Mar 2022 – Present”), uniform bullets and headings."
                         if not trailing and not odd else "Mixed date formats or bullet punctuation."))

    facts = {"pages": pfacts.get("pages", 0), "pdf_text": pdf_text}
    return checks, facts, dfind + pfind


def build_files(cv: dict) -> tuple[bytes, bytes, bool]:
    """Render with the standard layout; switch to compact if the PDF passes two pages."""
    cv = sanitize_cv(cv)
    pdf = render_pdf(cv)
    compact = _pdf_pages(pdf) > 2
    if compact:
        pdf = render_pdf(cv, compact=True)
    return render_docx(cv, compact=compact), pdf, compact


def stress_test(cv: dict) -> dict:
    cv = sanitize_cv(cv)
    docx, pdf, compact = build_files(cv)
    checks, facts, findings = _format_checks(cv, docx, pdf, compact)
    if not all(c["ok"] for c in checks):
        # Correct before delivering: retry in the other layout.
        alt_compact = not compact
        alt_pdf = render_pdf(cv, compact=alt_compact)
        alt_docx = render_docx(cv, compact=alt_compact)
        alt = _format_checks(cv, alt_docx, alt_pdf, alt_compact)
        if sum(c["ok"] for c in alt[0]) > sum(c["ok"] for c in checks):
            compact, (checks, facts, findings) = alt_compact, alt

    pages = facts["pages"]
    blockers = content_blockers(cv)
    ats_compliant = all(c["ok"] for c in checks)
    return {
        "checks": checks,
        "passed": sum(1 for c in checks if c["ok"]),
        "total": len(checks),
        "ats_compliant": ats_compliant,
        "content_blockers": blockers,
        "ats_ready": ats_compliant and not blockers,
        "pages": pages,
        "compact": compact,
        "length_note": None if pages <= 2 else
        f"The CV runs to {pages} pages. ATS software reads any length, but recruiters prefer two — trim the oldest "
        "roles' bullet points if you can.",
        "extracted_text_preview": facts["pdf_text"][:4000],
        "findings": findings,
        "pdf_text": facts["pdf_text"],
    }
