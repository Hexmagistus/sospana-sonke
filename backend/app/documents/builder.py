"""Build a tailored CV data structure from the candidate's real profile data.

Tailoring = truthful selection and re-ordering only (blueprint section 11). We
emphasise experience/skills relevant to the vacancy and write a summary from real
fields, but we NEVER add a skill, employer, qualification, or number the candidate
did not provide. The output is validated by the truthfulness checker before use.
"""
from __future__ import annotations

import re


def _nat_join(items: list[str]) -> str:
    """Join a list into natural English: 'A', 'A and B', 'A, B and C'."""
    items = [i for i in items if i]
    if len(items) <= 1:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + " and " + items[-1]


def _order_skills(skills: list[str], vacancy_skill_terms: set[str]) -> list[str]:
    relevant, others = [], []
    for s in skills:
        (relevant if s.lower() in vacancy_skill_terms else others).append(s)
    # Preserve original order within each group; relevant first.
    return relevant + others


def _order_experience(experience: list[dict]) -> list[dict]:
    def key(e):
        return (0 if e.get("is_current") else 1, _neg_date(e.get("start_date")))
    return sorted(experience, key=key)


def _neg_date(value) -> str:
    # Sort most-recent first; missing dates sort last.
    return "0000" if not value else "".join(c for c in str(value) if c.isdigit())[:8].rjust(8, "0")[::-1]


def build_summary(facts: dict, vacancy_title: str | None, top_skills: list[str] | None = None) -> str:
    """A truthful, professional 2–3 sentence summary built ONLY from real fields.

    No skill, number, industry, or achievement is invented — every clause maps to
    a value the candidate actually provided.
    """
    role = facts.get("current_occupation") or (facts.get("desired_occupations") or [None])[0]
    years = facts.get("years_experience")
    industries = facts.get("industries") or []
    top_skills = top_skills or []
    parts: list[str] = []

    # Sentence 1 — who they are.
    if role:
        lead = role
        if years:
            lead += f" with {years} year{'s' if years != 1 else ''} of experience"
        if industries:
            lead += f" across {_nat_join(industries[:3])}"
        parts.append(lead + ".")
    elif years:
        parts.append(f"Experienced professional with {years} year{'s' if years != 1 else ''} of experience.")

    # Sentence 2 — core strengths (real skills only).
    if top_skills:
        parts.append(f"Skilled in {_nat_join(top_skills[:5])}.")

    # Sentence 3 — the target role (truthful intent, not a claim of fit).
    if vacancy_title and vacancy_title.strip().lower() != "the role":
        parts.append(f"Seeking to bring this experience to the {vacancy_title} role.")

    return " ".join(parts).strip()


def build_tailored_cv(facts: dict, vacancy: dict | None = None) -> dict:
    """facts: flattened profile+user data. vacancy: {title, skill_terms:set}."""
    vacancy = vacancy or {}
    vacancy_terms = set(vacancy.get("skill_terms") or set())
    skills = _order_skills(list(facts.get("skills") or []), vacancy_terms)
    experience = _order_experience(list(facts.get("experience") or []))

    return {
        "full_name": facts.get("full_name") or "",
        "email": facts.get("email"),
        "phone": facts.get("phone"),
        "city": facts.get("city"),
        "country": facts.get("country"),
        "linkedin_url": facts.get("linkedin_url"),
        "github_url": facts.get("github_url"),
        "portfolio_url": facts.get("portfolio_url"),
        "summary": build_summary(facts, vacancy.get("title"), skills),
        "skills": skills,
        "experience": experience,
        "education": list(facts.get("education") or []),
        "certifications": list(facts.get("certifications") or []),
        "languages": list(facts.get("languages") or []),
        "drivers_licence": facts.get("drivers_licence"),
        "target_vacancy_title": vacancy.get("title"),
    }


def safe_filename(*parts: str) -> str:
    raw = "_".join(p for p in parts if p)
    return re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_") or "document"
