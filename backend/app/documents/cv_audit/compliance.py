"""ATS-compliance guard for every rebuilt CV that leaves the platform.

``sanitize_cv`` runs inside both renderers, so a DOCX or PDF can only ever be
produced from text an ATS parses cleanly, whatever the parser found or the
candidate typed on the edit screen:

- no emoji, dingbats, private-use or box-drawing glyphs (they extract as junk);
- no tab stops, control characters or runs of spaces (they break reading order);
- one date format everywhere ("Mar 2022 – Present");
- bullets without leading bullet glyphs, trailing full stops or duplicates;
- every field length-capped so one runaway paragraph cannot wreck the layout.

Content an ATS needs but only the candidate can supply (email, phone, dates,
job titles) is never invented. ``content_blockers`` lists what is missing so
the page can show exactly what stands between the CV and full compliance.
"""
from __future__ import annotations

import re
import unicodedata

from app.documents.cv_audit.parse import DATE_RANGE, SINGLE_DATE, norm_date

# Characters ATS parsers commonly mangle. Ordinary punctuation, accented
# letters, the en dash and the round bullet the renderer adds itself are kept.
_JUNK = re.compile(
    "["
    "\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f"   # control characters
    "​-‏‪-‮⁠-⁤﻿"  # zero-width and direction marks
    "←-⇿"                          # arrows
    "─-➿"                          # box drawing, shapes, misc symbols, dingbats
    "⬀-⯿"                          # misc symbols and arrows
    "-"                          # private use (Word symbol-font bullets)
    "︀-️￼�￾￿"  # variation selectors, replacement chars
    "\U0001f000-\U0001faff"                  # emoji and pictographs
    "\U000e0000-\U000e007f"                  # tags
    "]"
)
_LEADING_GLYPH = re.compile(r"^[\s•·▪▫■□◦●○◆◇➢➤►▶✓✔✦✧❖*>\-–—]+")
_STAR_RATING = re.compile(r"[★☆]+|\(\s*\d+\s*/\s*\d+\s*\)|\b\d\s*/\s*(?:5|10)\b")

MAX_WORD = 32  # longer runs get broken mid-word by the PDF line wrap and extract as two tokens
_URLISH = re.compile(r"^(?:https?://|www\.)|@|\.(?:com|org|net|co\.za|ac\.za|gov\.za)\b", re.I)


def _split_long_words(s: str) -> str:
    out = []
    for w in s.split(" "):
        if len(w) > MAX_WORD and not _URLISH.search(w):
            w = " ".join(w[i:i + MAX_WORD] for i in range(0, len(w), MAX_WORD))
        out.append(w)
    return " ".join(out)


LIMITS = {"short": 160, "line": 300, "summary": 1200, "bullet": 400}
MAX_BULLETS_PER_ROLE = 10


def clean_text(value, limit: int = LIMITS["line"]) -> str:
    if value is None:
        return ""
    s = unicodedata.normalize("NFC", str(value))
    s = s.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    s = s.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    s = _STAR_RATING.sub("", s)
    s = _JUNK.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = _split_long_words(s)
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(",;:") or s[:limit]
    return s


def clean_bullet(value) -> str:
    s = clean_text(value, LIMITS["bullet"])
    s = _LEADING_GLYPH.sub("", s).strip()
    s = s.rstrip(" .;:")
    return (s[0].upper() + s[1:]) if s else ""


def clean_date(value) -> str | None:
    """Any date the candidate types becomes 'Mon YYYY', 'YYYY' or 'Present'."""
    s = clean_text(value, 40)
    if not s:
        return None
    if re.fullmatch(r"(?i)present|current|currently|now|to date|ongoing|date", s):
        return "Present"
    m = SINGLE_DATE.search(s)
    return norm_date(m.group(1)) if m else s


def clean_date_text(value) -> str | None:
    s = clean_text(value, 60)
    if not s:
        return None
    m = DATE_RANGE.search(s)
    if m:
        return f"{norm_date(m.group(1))} – {norm_date(m.group(2))}"
    found = SINGLE_DATE.findall(s)
    return norm_date(found[-1]) if found else s


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for i in items:
        k = re.sub(r"[^a-z0-9]", "", i.lower())
        if i and k not in seen:
            seen.add(k)
            out.append(i)
    return out


def sanitize_cv(cv: dict) -> dict:
    cv = dict(cv or {})
    for f in ("full_name", "email", "phone", "location", "linkedin_url", "drivers_licence"):
        cv[f] = clean_text(cv.get(f), LIMITS["short"]) or None
    cv["headline"] = clean_text(cv.get("headline"), 200) or None
    cv["summary"] = clean_text(cv.get("summary"), LIMITS["summary"]) or None
    cv["links"] = [x for x in (clean_text(u, LIMITS["line"]) for u in (cv.get("links") or [])[:3]) if x]

    comp = {}
    for group, terms in (cv.get("competencies") or {}).items():
        g = clean_text(group, 80)
        ts = _dedupe([clean_text(t, 120).rstrip(".") for t in terms or []])
        if g and ts:
            comp[g] = ts[:12]
    cv["competencies"] = comp
    for key in ("software", "languages"):
        cv[key] = _dedupe([clean_text(t, 120) for t in cv.get(key) or []])[:20]

    exp = []
    for e in cv.get("experience") or []:
        e = dict(e)
        for f in ("position", "employer", "location"):
            e[f] = clean_text(e.get(f), LIMITS["short"]) or None
        e["is_current"] = bool(e.get("is_current"))
        e["start"] = clean_date(e.get("start"))
        e["end"] = "Present" if e["is_current"] else clean_date(e.get("end"))
        if e["end"] == "Present":
            e["is_current"] = True
        e["bullets"] = _dedupe([b for b in (clean_bullet(x) for x in e.get("bullets") or []) if b])[
            :MAX_BULLETS_PER_ROLE]
        if e["position"] or e["employer"] or e["bullets"]:
            exp.append(e)
    cv["experience"] = exp

    for key in ("education", "current_studies"):
        rows = []
        for ed in cv.get(key) or []:
            ed = dict(ed)
            for f in ("qualification", "institution"):
                ed[f] = clean_text(ed.get(f), LIMITS["short"]) or None
            ed["date_text"] = clean_date_text(ed.get("date_text"))
            if ed["qualification"] or ed["institution"]:
                rows.append(ed)
        cv[key] = rows

    for key in ("certifications", "short_courses", "in_progress_certs", "registrations"):
        rows = []
        for c in cv.get(key) or []:
            c = dict(c)
            c["name"] = clean_text(c.get("name"), LIMITS["short"])
            c["issuer"] = clean_text(c.get("issuer"), LIMITS["short"]) or None
            c["year"] = clean_text(c.get("year"), 20) or None
            if c["name"]:
                rows.append(c)
        cv[key] = rows

    refs = []
    for r in (cv.get("references") or [])[:5]:
        r = dict(r)
        r["name"] = clean_text(r.get("name"), 120) or None
        r["details"] = clean_text(r.get("details"), 200) or None
        r["phone"] = clean_text(r.get("phone"), 40) or None
        r["email"] = clean_text(r.get("email"), 160) or None
        if r["name"]:
            refs.append(r)
    cv["references"] = refs
    cv["references_on_request"] = bool(cv.get("references_on_request")) and not refs

    for key in ("projects", "achievements"):
        cv[key] = _dedupe([b for b in (clean_bullet(x) for x in cv.get(key) or []) if b])[:8]
    return cv


def content_blockers(cv: dict) -> list[dict]:
    """What an ATS needs that only the candidate can supply. Never guessed."""
    out = []

    def add(field: str, message: str):
        out.append({"field": field, "message": message})

    if not cv.get("full_name"):
        add("full_name", "Add your full name.")
    if not cv.get("email"):
        add("email", "Add an email address — without it an ATS cannot create your candidate record.")
    if not cv.get("phone"):
        add("phone", "Add a phone number.")
    if not cv.get("experience") and not cv.get("education"):
        add("experience", "Add at least one role or qualification.")
    for e in cv.get("experience") or []:
        label = e.get("position") or e.get("employer") or "a role"
        if not e.get("position"):
            add("experience", f"Add the job title for “{label}”.")
        if not e.get("employer"):
            add("experience", f"Add the employer for “{label}”.")
        if not e.get("start"):
            add("experience", f"Add the start date for “{label}”.")
        if not e.get("is_current") and not e.get("end"):
            add("experience", f"Add the end date for “{label}” (or mark it as your current job).")
    for ed in (cv.get("education") or []) + (cv.get("current_studies") or []):
        if ed.get("qualification") and not ed.get("institution"):
            add("education", f"Add the institution for “{ed['qualification']}”.")
    return out
