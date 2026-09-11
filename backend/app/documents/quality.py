"""CV Quality Score (blueprint: CV Quality Score & improvement guidance).

Rule-based and deterministic, over the CV's OWN content only — every
sub-score and suggestion is computed from data the candidate actually
supplied, never a claim about the candidate that isn't visible in it, and
never a suggestion to add a fact rather than better express one already
given. Reuses app/documents/ats.py for the ATS/keyword/structure figures
rather than recomputing them, and takes the deterministic match score
(app/matching/engine.py) as the Job Relevance figure when one is available.
"""
from __future__ import annotations

import re

from app.common.vocab import ACTION_VERBS, WEAK_RESUME_PHRASES
from app.documents.ats import score_ats


def _bullets_of(cv: dict) -> list[str]:
    out: list[str] = []
    for e in cv.get("experience", []) or []:
        for key in ("responsibilities", "achievements"):
            val = e.get(key)
            if val:
                out.extend(p.strip() for p in re.split(r"[\n;•]", str(val)) if p.strip())
    return out


def _content_quality(cv: dict) -> float:
    checks = [
        bool(cv.get("summary") and len(cv["summary"].split()) >= 8),
        bool(cv.get("skills") and len(cv["skills"]) >= 3),
        bool(cv.get("experience")),
        bool(cv.get("education")),
        bool(cv.get("email") and cv.get("phone")),
    ]
    return round(sum(checks) / len(checks) * 100, 1)


def _professional_language(cv: dict) -> tuple[float, list[str]]:
    bullets = _bullets_of(cv)
    text_blob = " ".join([*bullets, cv.get("summary") or ""]).lower()
    if not text_blob.strip():
        return 70.0, []
    suggestions: list[str] = []
    weak_hits = sum(text_blob.count(p) for p in WEAK_RESUME_PHRASES)
    first_person = len(re.findall(r"\bi\b", text_blob))
    strong_starts = sum(
        1 for b in bullets if b.split() and b.split()[0].lower().rstrip("s,.") in ACTION_VERBS
    )
    score = 100.0
    if weak_hits:
        score -= min(30, weak_hits * 8)
        suggestions.append(
            "Some bullets use passive phrasing like “responsible for” — consider leading "
            "with a strong action verb instead (e.g. “Managed…”, “Coordinated…”), "
            "using your own wording."
        )
    if first_person:
        score -= min(15, first_person * 3)
        suggestions.append("CVs read more professionally in the third person — consider dropping “I”.")
    if bullets and strong_starts / len(bullets) < 0.3:
        score -= 10
        suggestions.append("Start more of your bullet points with a strong action verb.")
    return max(0.0, round(score, 1)), suggestions


def _readability(cv: dict) -> tuple[float, list[str]]:
    bullets = _bullets_of(cv)
    if not bullets:
        return 70.0, []
    lengths = [len(b.split()) for b in bullets]
    avg = sum(lengths) / len(lengths)
    too_long = sum(1 for n in lengths if n > 30)
    suggestions: list[str] = []
    score = 100.0
    if avg > 28:
        score -= 20
        suggestions.append("Some bullet points run long — aim for roughly one line (12–20 words) each.")
    if too_long:
        score -= min(20, too_long * 5)
    return max(0.0, round(score, 1)), suggestions


def _achievement_focus(cv: dict) -> tuple[float, list[str]]:
    exp = cv.get("experience") or []
    if not exp:
        return 50.0, []
    with_achievement = sum(1 for e in exp if (e.get("achievements") or "").strip())
    score = round(with_achievement / len(exp) * 100, 1)
    suggestions: list[str] = []
    if with_achievement < len(exp):
        suggestions.append(
            "Add a specific achievement to each role where you can — a real outcome, volume or "
            "target you actually met. We never invent figures for you, so only add numbers you can "
            "stand behind."
        )
    return score, suggestions


def score_cv_quality(cv: dict, vacancy_skill_terms: set[str] | None = None,
                     match_score: float | None = None) -> dict:
    """Returns {"overall": float, "breakdown": {...8 sub-scores...}, "suggestions": [...]}."""
    vacancy_skill_terms = vacancy_skill_terms or set()
    ats_overall, ats_breakdown = score_ats(cv, vacancy_skill_terms)

    content = _content_quality(cv)
    relevance = round(match_score, 1) if match_score is not None else ats_breakdown["keyword_relevance"]
    language, lang_sugg = _professional_language(cv)
    readability, read_sugg = _readability(cv)
    achievement, achv_sugg = _achievement_focus(cv)

    breakdown = {
        "content_quality": content,
        "job_relevance": relevance,
        "professional_language": language,
        "ats_compatibility": ats_overall,
        "structure": ats_breakdown["structure"],
        "readability": readability,
        "achievement_focus": achievement,
        "keyword_alignment": ats_breakdown["keyword_relevance"],
    }
    weights = {
        "content_quality": 0.15, "job_relevance": 0.20, "professional_language": 0.10,
        "ats_compatibility": 0.20, "structure": 0.10, "readability": 0.10,
        "achievement_focus": 0.10, "keyword_alignment": 0.05,
    }
    overall = round(sum(breakdown[k] * w for k, w in weights.items()), 1)

    suggestions = [*lang_sugg, *read_sugg, *achv_sugg]
    if breakdown["keyword_alignment"] < 60:
        suggestions.append(
            "Your CV currently reflects only some of this job's key terms — check the Match "
            "Report for skills to add if you genuinely have them; we never add keywords that aren't "
            "truly yours."
        )
    return {"overall": overall, "breakdown": breakdown, "suggestions": suggestions}
