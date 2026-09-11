"""Heuristic job-description analysis for the "Tailor my CV to a job" flow.

Parses a candidate-pasted job advertisement into the same requirement shape the
scraper produces for a scraped vacancy (see app/scraper/extract.py), plus the
extra signal the CV builder needs on top: a guessed title/seniority,
categorised keywords, action verbs the advert itself uses, and named industry
mentions. Deterministic and rules-based, in keeping with the matching engine's
principle that an LLM never controls a business-logic decision — the same
advert always analyses the same way, and nothing here is invented: every
result is a direct extraction from the pasted text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.common.vocab import (
    SKILLS_BY_CATEGORY, ACTION_VERBS, SENIORITY_SIGNALS, RESPONSIBILITY_HINTS, INDUSTRY_TERMS,
)
from app.scraper.extract import classify_requirements, _classify_line, _BULLET_RE

_TITLE_LINE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 /&,'()\-]{2,80}$")
_SENIORITY_ORDER = ["Executive / Leadership", "Managerial", "Senior", "Mid-level",
                    "Graduate / Entry-level"]

# classify_requirements() (built for scraped ads that always have a clean
# "Requirements" heading) can mistake a SECOND, unrecognised section heading —
# e.g. "Key Responsibilities:" or a lone "Preferred:" — for a low-value "other"
# requirement, because it only resets out of "in a requirements section" mode
# on headings it recognises. A pasted advert has far more heading variety, so
# we drop these known heading-only lines rather than show them as if they were
# real requirements.
_HEADING_NOISE = {
    "responsibilities", "key responsibilities", "duties", "key duties",
    "preferred", "requirements", "minimum requirements", "key requirements",
    "about the role", "about you", "what you'll do", "what you will do",
    "the role", "overview", "desired", "nice to have", "qualifications",
    "what we offer", "benefits", "how to apply", "closing date",
}


def guess_title(text: str, hint: str | None) -> str:
    """Prefer whatever title the candidate typed; fall back to the first
    short, title-like line of the pasted advert (most job ads open with the
    role name); otherwise a neutral placeholder — never a guess presented as
    fact."""
    if hint and hint.strip():
        return hint.strip()[:300]
    for line in text.splitlines()[:6]:
        line = line.strip()
        if not line or len(line) > 80 or line.endswith((".", ":", ";")):
            continue
        if _TITLE_LINE_RE.match(line):
            words = line.split()
            if 1 <= len(words) <= 8:
                return line
    return "This role"


def guess_seniority(text: str, title: str) -> str:
    """Seniority signalled by the ADVERT's own wording — never a claim about
    the candidate. Checked most-senior-first so e.g. "Senior Manager" reports
    as Managerial rather than merely Senior."""
    blob = f"{title} {text}".lower()
    for level in _SENIORITY_ORDER:
        if any(kw in blob for kw in SENIORITY_SIGNALS[level]):
            return level
    return "Not specified in the advert"


def _categorised_keywords(text: str) -> dict[str, list[str]]:
    low = text.lower()
    out: dict[str, list[str]] = {}
    for category, terms in SKILLS_BY_CATEGORY.items():
        found = sorted({t for t in terms if re.search(r"\b" + re.escape(t) + r"\b", low)})
        if found:
            out[category] = found
    return out


def _action_verbs_used(text: str) -> list[str]:
    low = text.lower()
    return sorted({v for v in ACTION_VERBS if re.search(r"\b" + re.escape(v) + r"\b", low)})


def _industry_mentions(text: str) -> list[str]:
    low = text.lower()
    return sorted({t for t in INDUSTRY_TERMS if t in low})


def _responsibility_lines(text: str) -> list[dict]:
    """Duty/responsibility bullets that classify_requirements() drops because
    they carry no explicit must-have/preferred signal word (e.g. "Manage the
    daily production schedule") — still valuable for the candidate to see, and
    for the Responsibility-match sub-score."""
    out: list[dict] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        if not _BULLET_RE.match(raw_line):
            continue
        body = _BULLET_RE.sub("", raw_line).strip()
        if len(body) < 6:
            continue
        low = body.lower()
        first_word = low.split()[0] if low.split() else ""
        if first_word.rstrip("s") in ACTION_VERBS or any(h in low[:40] for h in RESPONSIBILITY_HINTS):
            key = low[:120]
            if key in seen:
                continue
            seen.add(key)
            out.append({"text": body[:400], "kind": "soft", "category": "responsibility",
                       "extracted_by": "rules"})
        if len(out) >= 25:
            break
    return out


def _fallback_sentence_requirements(text: str) -> list[dict]:
    """When the advert is plain prose with no bullets/headings at all,
    classify_requirements() finds nothing. Fall back to sentence-level
    classification so a prose-only advert still yields something."""
    out: list[dict] = []
    seen: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        s = sentence.strip()
        if len(s) < 15 or len(s) > 300:
            continue
        result = _classify_line(s, in_requirements=True)
        if result is None:
            continue
        key = s.lower()[:120]
        if key in seen:
            continue
        seen.add(key)
        kind, category = result
        out.append({"text": s[:400], "kind": kind, "category": category, "extracted_by": "rules"})
        if len(out) >= 25:
            break
    return out


@dataclass
class JobAnalysisResult:
    title: str
    seniority: str
    requirements: list[dict] = field(default_factory=list)
    keywords: dict[str, list[str]] = field(default_factory=dict)
    action_verbs: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    requirement_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "seniority": self.seniority,
            "keywords": self.keywords,
            "action_verbs": self.action_verbs,
            "industries": self.industries,
            "requirements": self.requirements,
            "requirement_counts": self.requirement_counts,
        }


def analyze_description(text: str, title_hint: str | None = None) -> JobAnalysisResult:
    text = text or ""
    title = guess_title(text, title_hint)
    seniority = guess_seniority(text, title)

    requirements = classify_requirements(text)
    requirements = [r for r in requirements if r["text"].strip(" :").lower() not in _HEADING_NOISE]
    if not requirements:
        requirements = _fallback_sentence_requirements(text)

    # classify_requirements() files an uncategorised duty bullet (no hard/soft
    # signal word) under "other" rather than dropping it. Recognise the ones
    # that are clearly a job duty so they group with the rest of the
    # Responsibility-match sub-score instead of the generic "other" bucket.
    for r in requirements:
        if r["category"] == "other":
            low = r["text"].lower()
            first_word = low.split()[0] if low.split() else ""
            if first_word.rstrip("s") in ACTION_VERBS or any(h in low[:40] for h in RESPONSIBILITY_HINTS):
                r["category"] = "responsibility"

    existing = {r["text"].lower()[:120] for r in requirements}
    for r in _responsibility_lines(text):
        if r["text"].lower()[:120] not in existing:
            requirements.append(r)

    counts: dict[str, int] = {}
    for r in requirements:
        counts[r["category"]] = counts.get(r["category"], 0) + 1

    return JobAnalysisResult(
        title=title, seniority=seniority, requirements=requirements,
        keywords=_categorised_keywords(text), action_verbs=_action_verbs_used(text),
        industries=_industry_mentions(text), requirement_counts=counts,
    )
