"""ATS compatibility scoring (blueprint section 33).

Produces a 0-100 compatibility score with a breakdown across keyword relevance,
structure, contact info, and readability. This is guidance, not a guarantee of
selection (the UI must say so).
"""
from __future__ import annotations


def score_ats(cv_data: dict, vacancy_skill_terms: set[str]) -> tuple[float, dict]:
    # Keyword relevance: how many of the vacancy's skill terms appear in the CV.
    cv_skills = {s.lower() for s in cv_data.get("skills", [])}
    if vacancy_skill_terms:
        matched = vacancy_skill_terms & cv_skills
        keyword = len(matched) / len(vacancy_skill_terms) * 100
    else:
        keyword = 80.0  # nothing specific to match against

    # Structure: presence of the standard sections an ATS expects.
    sections_present = sum([
        bool(cv_data.get("summary")),
        bool(cv_data.get("skills")),
        bool(cv_data.get("experience")),
        bool(cv_data.get("education")),
    ])
    structure = sections_present / 4 * 100

    # Contact info completeness.
    contact_bits = sum([bool(cv_data.get("full_name")), bool(cv_data.get("email")),
                        bool(cv_data.get("phone"))])
    contact = contact_bits / 3 * 100

    # Readability: the templates are plain text (no tables/graphics/columns), which
    # is exactly what ATS parsers prefer, so this scores high by construction.
    readability = 96.0

    overall = round(0.45 * keyword + 0.25 * structure + 0.15 * contact + 0.15 * readability, 1)
    breakdown = {
        "keyword_relevance": round(keyword, 1),
        "structure": round(structure, 1),
        "contact_info": round(contact, 1),
        "readability": readability,
    }
    return overall, breakdown
