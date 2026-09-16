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


# ---- structured filters: province / salary / NQF ---------------------------
# All three are additive, best-effort signals derived from the free-text fields a
# scraper already captured (location/salary/title/description). None of them ever
# replaces or overrides the original free text shown to a candidate — a None here
# just means the filter can't be applied to that listing, not that the data is
# wrong.

SA_PROVINCES = [
    "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
    "Mpumalanga", "Northern Cape", "North West", "Western Cape",
]

_CITY_TO_PROVINCE = {
    "johannesburg": "Gauteng", "joburg": "Gauteng", "pretoria": "Gauteng",
    "tshwane": "Gauteng", "vereeniging": "Gauteng", "vanderbijlpark": "Gauteng",
    "sandton": "Gauteng", "soweto": "Gauteng", "centurion": "Gauteng",
    "midrand": "Gauteng", "randburg": "Gauteng", "boksburg": "Gauteng",
    "durban": "KwaZulu-Natal", "pietermaritzburg": "KwaZulu-Natal",
    "newcastle": "KwaZulu-Natal", "richards bay": "KwaZulu-Natal",
    "umhlanga": "KwaZulu-Natal",
    "cape town": "Western Cape", "stellenbosch": "Western Cape",
    "george": "Western Cape", "paarl": "Western Cape", "bellville": "Western Cape",
    "port elizabeth": "Eastern Cape", "gqeberha": "Eastern Cape",
    "east london": "Eastern Cape", "mthatha": "Eastern Cape",
    "bloemfontein": "Free State", "welkom": "Free State",
    "polokwane": "Limpopo", "tzaneen": "Limpopo", "louis trichardt": "Limpopo",
    "nelspruit": "Mpumalanga", "mbombela": "Mpumalanga", "witbank": "Mpumalanga",
    "emalahleni": "Mpumalanga", "secunda": "Mpumalanga",
    "kimberley": "Northern Cape", "upington": "Northern Cape",
    "rustenburg": "North West", "mahikeng": "North West", "klerksdorp": "North West",
    "potchefstroom": "North West",
}


def infer_province(location: str | None) -> str | None:
    """Best-effort South African province from a free-text location string.

    Returns None (never a guess) when the text doesn't clearly name a province or a
    recognised city — used only to *narrow* an existing free-text location for
    filtering, never to replace what's shown to a candidate.
    """
    if not location:
        return None
    text = location.lower()
    for province in SA_PROVINCES:
        if province.lower() in text:
            return province
    for city, province in _CITY_TO_PROVINCE.items():
        if city in text:
            return province
    return None


_SALARY_K_RANGE_RE = re.compile(r"r?\s*([\d.]+)\s*k\s*(?:-|to|–)\s*r?\s*([\d.]+)\s*k", re.IGNORECASE)
_SALARY_RANGE_RE = re.compile(r"r?\s*([\d,]{4,})\s*(?:-|to|–)\s*r?\s*([\d,]{4,})", re.IGNORECASE)
_SALARY_SINGLE_RE = re.compile(r"r\s*([\d,]{4,})", re.IGNORECASE)


def parse_salary_range(salary_text: str | None) -> tuple[int | None, int | None]:
    """Best-effort monthly ZAR (min, max) parsed from a free-text salary string.

    Never fabricates a figure — returns (None, None) whenever the text doesn't
    contain a recognisable number (e.g. "Market related", "Negotiable"). Handles
    "R15,000 - R20,000", "R15k - R20k", and a single figure ("R18,000", used as
    both min and max).
    """
    if not salary_text:
        return None, None
    text = salary_text.strip()
    m = _SALARY_K_RANGE_RE.search(text)
    if m:
        try:
            lo = int(float(m.group(1)) * 1000)
            hi = int(float(m.group(2)) * 1000)
            return min(lo, hi), max(lo, hi)
        except ValueError:
            pass
    m = _SALARY_RANGE_RE.search(text)
    if m:
        try:
            lo = int(m.group(1).replace(",", ""))
            hi = int(m.group(2).replace(",", ""))
            return min(lo, hi), max(lo, hi)
        except ValueError:
            pass
    m = _SALARY_SINGLE_RE.search(text)
    if m:
        try:
            val = int(m.group(1).replace(",", ""))
            return val, val
        except ValueError:
            pass
    return None, None


# NQF (National Qualifications Framework) keyword ladder, most-specific phrases
# first so e.g. "national diploma" matches before the bare "diploma" fallback.
# South Africa's NQF runs 1 (Grade 9) to 10 (Doctorate) per SAQA. This is a rough
# *estimate* of the qualification level a listing is asking for, from whatever
# keywords appear in its own title/description — it is surfaced as an estimated
# filter/sort signal, never presented as an authoritative SAQA rating.
_NQF_KEYWORDS: list[tuple[str, int]] = [
    ("doctorate", 10), ("phd", 10),
    ("master's", 9), ("masters", 9), ("mba", 9),
    ("honours", 8), ("honour's", 8), ("postgraduate diploma", 8),
    ("bachelor", 7), ("degree", 7), ("advanced diploma", 7),
    ("national diploma", 6), ("diploma", 6),
    ("higher certificate", 5),
    ("n4", 4), ("n5", 4), ("n6", 4), ("matric", 4), ("grade 12", 4), ("nqf 4", 4),
    ("grade 9", 1), ("nqf 1", 1),
]


def infer_nqf_level(title: str | None, description: str | None) -> int | None:
    blob = f"{title or ''} {description or ''}".lower()
    for keyword, level in _NQF_KEYWORDS:
        if keyword in blob:
            return level
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
