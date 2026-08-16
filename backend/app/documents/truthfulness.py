"""Truthfulness validation for generated CVs (blueprint sections 2, 11 & 34).

The single most important guardrail: every factual claim in a generated CV must be
backed by the candidate's own profile data. This runs on EVERY generated document,
so that if an AI-drafted variant ever introduces an unsupported skill, employer,
qualification, or an inflated years-of-experience figure, it is caught and flagged
rather than sent to an employer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ProfileFacts:
    skills: set[str] = field(default_factory=set)          # lowercased
    employers: set[str] = field(default_factory=set)       # lowercased
    institutions: set[str] = field(default_factory=set)    # lowercased
    certifications: set[str] = field(default_factory=set)  # lowercased
    years_experience: int | None = None


@dataclass
class TruthResult:
    ok: bool
    violations: list[str] = field(default_factory=list)


def validate_cv(cv_data: dict, facts: ProfileFacts) -> TruthResult:
    violations: list[str] = []

    for s in cv_data.get("skills", []):
        if s.strip().lower() not in facts.skills:
            violations.append(f"Skill not in profile: '{s}'")

    for e in cv_data.get("experience", []):
        emp = (e.get("employer") or "").strip().lower()
        if emp and emp not in facts.employers:
            violations.append(f"Employer not in profile: '{e.get('employer')}'")

    for ed in cv_data.get("education", []):
        inst = (ed.get("institution") or "").strip().lower()
        if inst and inst not in facts.institutions:
            violations.append(f"Institution not in profile: '{ed.get('institution')}'")

    for c in cv_data.get("certifications", []):
        name = (c.get("name") or "").strip().lower()
        if name and name not in facts.certifications:
            violations.append(f"Certification not in profile: '{c.get('name')}'")

    # No inflated experience claim in the summary.
    summary = cv_data.get("summary") or ""
    for m in re.finditer(r"(\d+)\s*year", summary, re.I):
        claimed = int(m.group(1))
        if facts.years_experience is None or claimed > facts.years_experience:
            violations.append(
                f"Summary claims {claimed} years but profile has "
                f"{facts.years_experience if facts.years_experience is not None else 'none'}.")

    return TruthResult(ok=not violations, violations=violations)
