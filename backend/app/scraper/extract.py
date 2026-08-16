"""Vacancy normalisation, content hashing, and requirement classification.

Turns a RawVacancy into the fields we store, computes a stable content hash for
deduplication (blueprint section 7), and splits requirements into HARD vs SOFT
using deterministic rules (section 9). The hard/soft split is intentionally
rules-based, not AI — it drives matching decisions and must be predictable.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime

from app.scraper.base import RawVacancy

# ---- normalisation ----------------------------------------------------------

def normalize_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ", "%d/%m/%Y", "%d %B %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value[:len(fmt) + 6], fmt).date()
        except ValueError:
            continue
    # ISO with timezone offset
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def infer_work_mode(raw: RawVacancy) -> str | None:
    if raw.work_mode:
        wm = raw.work_mode.lower()
        if "remote" in wm:
            return "remote"
        if "hybrid" in wm:
            return "hybrid"
        if "office" in wm or "onsite" in wm or "on-site" in wm:
            return "onsite"
    blob = f"{raw.location or ''} {raw.title or ''} {raw.description or ''}".lower()
    if "hybrid" in blob:
        return "hybrid"
    if "remote" in blob or "work from home" in blob:
        return "remote"
    return None


def content_hash(company_id: str, raw: RawVacancy) -> str:
    basis = "|".join([
        company_id,
        (raw.title or "").strip().lower(),
        (raw.location or "").strip().lower(),
        (raw.external_id or "").strip().lower(),
        (raw.description or "").strip().lower()[:2000],
    ])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


# ---- requirement classification --------------------------------------------

_HARD_SIGNALS = ["must have", "must be", "required", "requirement", "essential", "mandatory",
                 "minimum of", "at least", "you will need", "non-negotiable", "proven",
                 "registered with", "valid driver", "degree in", "matric"]
_SOFT_SIGNALS = ["preferred", "advantageous", "advantage", "beneficial", "desirable",
                 "nice to have", "a plus", "ideally", "bonus", "would be"]

_CATEGORY_PATTERNS = [
    ("experience", re.compile(r"\byears?\b.*\bexperience\b|\bexperience\b", re.I)),
    ("qualification", re.compile(r"\bdegree|diploma|matric|grade\s*12|bachelor|honours|master|mba|qualification|b\.?com|b\.?sc\b", re.I)),
    ("certification", re.compile(r"\bcertif|accredit", re.I)),
    ("registration", re.compile(r"\bregist|ecsa|saica|sacnasp|hpcsa|professional body\b", re.I)),
    ("licence", re.compile(r"\blicen[cs]e\b|driver'?s? licen", re.I)),
    ("skill", re.compile(r"\bskill|proficien|knowledge of|competen|ability to\b", re.I)),
]

_HEADING_RE = re.compile(r"(requirements|qualifications|what you.{0,5}need|minimum requirements|"
                         r"key requirements|experience|skills|competencies)", re.I)
_BULLET_RE = re.compile(r"^\s*[-*•▪◦·]\s+|^\s*\d+[.)]\s+")


def _classify_line(line: str, in_requirements: bool) -> tuple[str, str] | None:
    low = line.lower()
    kind = "soft" if any(s in low for s in _SOFT_SIGNALS) else None
    if kind is None:
        kind = "hard" if any(s in low for s in _HARD_SIGNALS) else None
    if kind is None:
        # Inside a requirements section, an unqualified item leans hard-ish but we
        # stay cautious and mark it soft unless a hard signal is present.
        if not in_requirements:
            return None
        kind = "soft"
    category = "other"
    for name, pat in _CATEGORY_PATTERNS:
        if pat.search(low):
            category = name
            break
    return kind, category


def classify_requirements(description: str | None) -> list[dict]:
    if not description:
        return []
    out: list[dict] = []
    in_req = False
    seen: set[str] = set()
    for raw_line in description.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        is_bullet = bool(_BULLET_RE.match(raw_line))
        text = _BULLET_RE.sub("", raw_line).strip()
        # A short, non-bullet line that names a section is a heading, not a requirement.
        if not is_bullet and _HEADING_RE.search(line) and len(line) < 40:
            in_req = True
            continue
        if not text or len(text) < 4:
            continue
        # Only treat bullets, or lines within a requirements section, as candidate requirements.
        if not (is_bullet or in_req):
            continue
        result = _classify_line(text, in_req)
        if result is None:
            continue
        key = text.lower()[:120]
        if key in seen:
            continue
        seen.add(key)
        kind, category = result
        out.append({"text": text[:500], "kind": kind, "category": category, "extracted_by": "rules"})
        if len(out) >= 40:
            break
    return out
