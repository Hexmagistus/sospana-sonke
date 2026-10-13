"""Opportunity type for a stored role.

A row stays a job unless the title, or failing that the description, names
exactly one of internship, learnership, bursary, or graduate programme.
Two names, or a mention that reads as a requirement the applicant already
holds, stay a job. Field of study and stipend are copied only when the text
labels them. Nothing here invents a closing date.
"""
from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

JOB = "job"
INTERNSHIP = "internship"
LEARNERSHIP = "learnership"
BURSARY = "bursary"
GRADUATE_PROGRAMME = "graduate_programme"

OPPORTUNITY_TYPES = (
    JOB,
    INTERNSHIP,
    LEARNERSHIP,
    BURSARY,
    GRADUATE_PROGRAMME,
)

_TYPE_LABELS = {
    JOB: "job",
    INTERNSHIP: "internship",
    LEARNERSHIP: "learnership",
    BURSARY: "bursary",
    GRADUATE_PROGRAMME: "graduate programme",
}

# Order does not matter: a single hit is kept, and more than one hit is a job.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (LEARNERSHIP, re.compile(r"\blearnerships?\b", re.IGNORECASE)),
    (BURSARY, re.compile(r"\bbursar(?:y|ies)\b", re.IGNORECASE)),
    (GRADUATE_PROGRAMME, re.compile(r"\bgraduate\s+program(?:me)?s?\b", re.IGNORECASE)),
    (INTERNSHIP, re.compile(r"\binternships?\b|\bintern\b", re.IGNORECASE)),
)

# A mention just before the word is the applicant's history, not the opening.
_REQUIREMENT = re.compile(
    r"\b(?:completed|completing|previous|prior|must have|experience (?:of|in|with)|"
    r"holders? of|who have|required)\b.{0,40}$",
    re.IGNORECASE,
)

_FIELD = re.compile(
    r"\bfield of study\s*[:\-–]\s*([^\n.;]{2,80})",
    re.IGNORECASE,
)
_STIPEND = re.compile(
    r"\b(?:stipend|bursary (?:amount|value)|funding amount)\s*(?:of|:|\-|–)\s*([^\n.;]{2,80})",
    re.IGNORECASE,
)

_PREFILTER = """
lower(coalesce(title, '')) LIKE '%learn%'
OR lower(coalesce(title, '')) LIKE '%bursar%'
OR lower(coalesce(title, '')) LIKE '%intern%'
OR lower(coalesce(title, '')) LIKE '%graduate%'
OR lower(substr(coalesce(description, ''), 1, 1000)) LIKE '%learnership%'
OR lower(substr(coalesce(description, ''), 1, 1000)) LIKE '%bursar%'
OR lower(substr(coalesce(description, ''), 1, 1000)) LIKE '%internship%'
OR lower(substr(coalesce(description, ''), 1, 1000)) LIKE '% graduate program%'
"""


def type_label(kind: str | None) -> str:
    return _TYPE_LABELS.get(kind or JOB, _TYPE_LABELS[JOB])


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _hits(text: str) -> set[str]:
    found: set[str] = set()
    for name, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            prefix = text[max(0, match.start() - 60):match.start()]
            if _REQUIREMENT.search(prefix):
                continue
            found.add(name)
    return found


def classify_opportunity(title: str | None, description: str | None = None) -> str:
    """Return one opportunity type. Unclear text stays ``job``."""
    title_hits = _hits(title or "")
    if len(title_hits) == 1:
        return next(iter(title_hits))
    if len(title_hits) > 1:
        return JOB
    description_hits = _hits((description or "")[:4000])
    if len(description_hits) == 1:
        return next(iter(description_hits))
    return JOB


def _labelled(pattern: re.Pattern[str], title: str | None, description: str | None) -> str | None:
    blob = f"{title or ''}\n{description or ''}"
    match = pattern.search(blob)
    if match is None:
        return None
    text = _clean(match.group(1))[:200]
    if not any(ch.isalnum() for ch in text):
        return None
    return text


def stated_field_of_study(title: str | None, description: str | None = None) -> str | None:
    """The field of study only when the text labels it. Otherwise nothing."""
    return _labelled(_FIELD, title, description)


def stated_stipend(title: str | None, description: str | None = None) -> str | None:
    """Stipend or funding only as the text states it. Otherwise nothing."""
    return _labelled(_STIPEND, title, description)


def classify_stored(bind: Engine) -> int:
    """Label stored rows that are still jobs and whose text might name a programme.

    Rows that stay jobs are marked reviewed so the next boot does not read them
    again. A scan classifies its own rows and does not wait for this pass.
    Returns how many rows changed to a programme type.
    """
    changed = 0
    off = "0" if bind.dialect.name == "sqlite" else "FALSE"
    on = "1" if bind.dialect.name == "sqlite" else "TRUE"
    with bind.begin() as conn:
        rows = conn.execute(text(
            "SELECT id, title, substr(coalesce(description, ''), 1, 1000), last_seen_at "
            "FROM vacancies "
            f"WHERE opportunity_reviewed = {off} AND (" + _PREFILTER + ")"
        )).fetchall()
        for row_id, title, description, seen in rows:
            kind = classify_opportunity(title, description)
            study = stated_field_of_study(title, description)
            stipend = stated_stipend(title, description)
            verified = seen if kind != JOB else None
            conn.execute(
                text(
                    "UPDATE vacancies SET opportunity_type = :kind, "
                    "field_of_study = :study, stipend_text = :stipend, "
                    f"verified_at = :verified, opportunity_reviewed = {on} "
                    "WHERE id = :id"
                ),
                {
                    "kind": kind, "study": study, "stipend": stipend,
                    "verified": verified, "id": row_id,
                },
            )
            if kind != JOB:
                changed += 1
        conn.execute(text(
            "UPDATE vacancies SET opportunity_reviewed = " + on + " "
            "WHERE opportunity_reviewed = " + off
        ))
    return changed
