"""Deterministic candidate-vacancy matching engine (blueprint sections 8, 9, 10).

Pure functions over plain data — no database, no LLM — so scoring is predictable,
testable, and free. It produces per-dimension sub-scores, a weighted total, a
hard-requirement gate, an explainable decision, and human-readable reasons/gaps.
An LLM may later rephrase the reasons for the candidate, but it never changes the
score or the decision (blueprint: don't let an LLM control business logic).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.common.vocab import SKILL_TERMS, EDUCATION_RANK
from app.matching.config import MatchConfig

_YEARS_RE = re.compile(r"(\d+)\s*(?:\+|plus)?\s*year", re.I)


# ---- input data structures --------------------------------------------------

@dataclass
class CandidateData:
    years_experience: int | None = None
    skills: set[str] = field(default_factory=set)              # lowercased
    education_levels: set[str] = field(default_factory=set)    # e.g. {"degree", "honours"}
    certifications: set[str] = field(default_factory=set)      # lowercased names/tokens
    desired_occupations: list[str] = field(default_factory=list)
    current_occupation: str | None = None
    industries: set[str] = field(default_factory=set)          # lowercased
    preferred_locations: list[str] = field(default_factory=list)  # lowercased
    work_mode_preference: str | None = None
    willing_to_relocate: bool | None = None
    minimum_salary: int | None = None
    has_drivers_licence: bool = False

    @property
    def max_education_rank(self) -> int:
        return max((EDUCATION_RANK.get(lvl, 0) for lvl in self.education_levels), default=0)

    @property
    def data_richness(self) -> int:
        """A rough 0-4 measure of how much profile data we have, for confidence."""
        score = 0
        score += 1 if self.years_experience is not None else 0
        score += 1 if self.skills else 0
        score += 1 if self.education_levels else 0
        score += 1 if (self.desired_occupations or self.current_occupation) else 0
        return score


@dataclass
class VacancyData:
    title: str = ""
    location: str | None = None
    work_mode: str | None = None
    salary_amount: int | None = None
    description: str | None = None
    company_sector: str | None = None
    requirements: list[dict] = field(default_factory=list)  # {text, kind, category}

    @property
    def skill_terms(self) -> set[str]:
        blob = f"{self.title} {self.description or ''} " + " ".join(r["text"] for r in self.requirements)
        blob = blob.lower()
        return {t for t in SKILL_TERMS if re.search(r"\b" + re.escape(t) + r"\b", blob)}


@dataclass
class MatchResult:
    score: float
    sub_scores: dict[str, float]
    band: str
    decision: str
    confidence: str
    hard_ok: bool
    reasons: list[str]
    gaps: list[str]


# ---- requirement evaluation -------------------------------------------------

def _required_years(text: str) -> int | None:
    m = _YEARS_RE.search(text)
    return int(m.group(1)) if m else None


def _qualification_satisfied(cand: CandidateData, text: str) -> bool:
    low = text.lower()
    mentioned = [(kw, rank) for kw, rank in EDUCATION_RANK.items() if kw in low]
    if not mentioned:
        return cand.max_education_rank > 0  # generic "qualification" -> any qualification
    needed = min(rank for _, rank in mentioned)  # the lowest acceptable level named
    return cand.max_education_rank >= needed


def requirement_met(cand: CandidateData, req: dict) -> bool | None:
    """Return True/False if assessable, or None if we cannot judge from the profile."""
    text = req["text"].lower()
    category = req.get("category", "other")

    if category == "experience":
        need = _required_years(text)
        if need is None:
            return None
        if cand.years_experience is None:
            return None
        return cand.years_experience >= need

    if category == "qualification":
        return _qualification_satisfied(cand, text)

    if category in ("certification", "registration"):
        if not cand.certifications:
            return False
        return any(c in text or any(tok in text for tok in c.split()) for c in cand.certifications)

    if category == "licence":
        if "driver" in text:
            return cand.has_drivers_licence
        return None

    if category == "skill":
        return any(s in text for s in cand.skills) if cand.skills else False

    return None  # "other" — cannot deterministically judge


# ---- sub-scores (each 0-100) ------------------------------------------------

def _score_bucket(cand, vac, category) -> tuple[float, list[str], list[str]]:
    reqs = [r for r in vac.requirements if r.get("category") == category]
    if not reqs:
        return 100.0, [], []
    met = unmet = unknown = 0
    reasons, gaps = [], []
    for r in reqs:
        result = requirement_met(cand, r)
        if result is True:
            met += 1
        elif result is False:
            unmet += 1
            (gaps if r["kind"] == "hard" else gaps).append(
                f"{'Mandatory' if r['kind'] == 'hard' else 'Preferred'} {category} not evident: {r['text']}")
        else:
            unknown += 1
    assessable = met + unmet
    if assessable == 0:
        return 70.0, reasons, gaps  # present but not assessable -> neutral
    return (met / assessable) * 100.0, reasons, gaps


def score_experience(cand, vac) -> tuple[float, list[str], list[str]]:
    exp_reqs = [r for r in vac.requirements if r.get("category") == "experience"]
    needs = [n for n in (_required_years(r["text"]) for r in exp_reqs) if n is not None]
    if not needs:
        return (80.0 if cand.years_experience else 70.0), [], []
    need = max(needs)
    if cand.years_experience is None:
        return 40.0, [], [f"Vacancy asks for {need}+ years; your profile does not state years of experience."]
    ratio = min(cand.years_experience / need, 1.0) if need > 0 else 1.0
    if cand.years_experience >= need:
        return 100.0, [f"Meets required experience ({cand.years_experience} years, needs {need})."], []
    return ratio * 100.0, [], [f"Required experience {need} years; your profile shows {cand.years_experience}."]


def score_skills(cand, vac) -> tuple[float, list[str], list[str]]:
    needed = vac.skill_terms
    if not needed:
        return 70.0, [], []
    matched = needed & cand.skills
    coverage = len(matched) / len(needed) * 100.0
    reasons, gaps = [], []
    if matched:
        reasons.append(f"Has {len(matched)} of {len(needed)} relevant skills: {', '.join(sorted(matched))}.")
    missing = needed - cand.skills
    if missing:
        gaps.append(f"Skills to strengthen: {', '.join(sorted(missing))}.")
    return coverage, reasons, gaps


def _token_overlap(a: str, b: str) -> float:
    ta = {t for t in re.findall(r"[a-z]+", a.lower()) if len(t) > 2}
    tb = {t for t in re.findall(r"[a-z]+", b.lower()) if len(t) > 2}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def score_title(cand, vac) -> tuple[float, list[str], list[str]]:
    targets = list(cand.desired_occupations)
    if cand.current_occupation:
        targets.append(cand.current_occupation)
    if not targets:
        return 60.0, [], []
    best = max(_token_overlap(vac.title, t) for t in targets)
    if best >= 0.5:
        return 100.0, [f"Role aligns with your target occupation ('{vac.title}')."], []
    if best >= 0.25:
        return 70.0, [], []
    return 40.0, [], [f"Role title ('{vac.title}') differs from your stated target roles."]


def score_industry(cand, vac) -> tuple[float, list[str], list[str]]:
    if not cand.industries:
        return 70.0, [], []
    sector = (vac.company_sector or "").lower()
    if sector and any(ind in sector or sector in ind for ind in cand.industries):
        return 100.0, ["Relevant industry experience."], []
    return 45.0, [], []


def score_location(cand, vac) -> tuple[float, list[str], list[str]]:
    if (vac.work_mode or "").lower() == "remote":
        return 100.0, ["Remote role — location is not a barrier."], []
    if not cand.preferred_locations:
        return 80.0, [], []
    loc = (vac.location or "").lower()
    if loc and any(pl in loc or loc in pl for pl in cand.preferred_locations):
        return 100.0, ["Location matches your preferences."], []
    if cand.willing_to_relocate:
        return 70.0, ["Outside preferred location, but you are open to relocating."], []
    return 20.0, [], [f"Location ('{vac.location}') is outside your preferred areas."]


# ---- top-level match --------------------------------------------------------

_CRITICAL_HARD = {"qualification", "experience", "certification", "registration", "licence"}


def evaluate_hard_gate(cand, vac) -> tuple[bool, list[str]]:
    """hard_ok is False if any HARD requirement in a critical category is clearly unmet."""
    gaps = []
    ok = True
    for r in vac.requirements:
        if r["kind"] != "hard":
            continue
        result = requirement_met(cand, r)
        if result is False and r.get("category") in _CRITICAL_HARD:
            ok = False
            gaps.append(f"Mandatory requirement not satisfied: {r['text']}")
    return ok, gaps


def match(cand: CandidateData, vac: VacancyData, config: MatchConfig | None = None) -> MatchResult:
    config = config or MatchConfig()

    q, qr, qg = _score_bucket(cand, vac, "qualification")
    e, er, eg = score_experience(cand, vac)
    s, sr, sg = score_skills(cand, vac)
    t, tr, tg = score_title(cand, vac)
    ind, ir, ig = score_industry(cand, vac)
    loc, lr, lg = score_location(cand, vac)
    cert, cr, cg = _score_bucket(cand, vac, "certification")

    sub = {"qualification": q, "experience": e, "skills": s, "title": t,
           "industry": ind, "location": loc, "certification": cert, "other": 70.0}

    total_weight = sum(config.weights.values()) or 1.0
    score = sum(sub[k] * config.weights.get(k, 0) for k in sub) / total_weight
    score = round(score, 1)

    hard_ok, hard_gaps = evaluate_hard_gate(cand, vac)

    reasons = [*qr, *er, *sr, *tr, *ir, *lr, *cr]
    gaps = [*hard_gaps, *qg, *eg, *sg, *tg, *ig, *lg, *cg]
    # de-dup while preserving order
    reasons = list(dict.fromkeys(reasons))
    gaps = list(dict.fromkeys(gaps))

    if not hard_ok:
        decision = "DO_NOT_APPLY"
    elif score >= config.apply_threshold:
        decision = "APPLY"
    elif score >= config.review_threshold:
        decision = "REVIEW"
    else:
        decision = "DO_NOT_APPLY"

    richness = cand.data_richness
    if richness >= 3 and (score >= config.bands["good"] or score < config.bands["weak"] or not hard_ok):
        confidence = "High"
    elif richness >= 2:
        confidence = "Medium"
    else:
        confidence = "Low"

    return MatchResult(score=score, sub_scores={k: round(v, 1) for k, v in sub.items()},
                       band=config.band_for(score), decision=decision, confidence=confidence,
                       hard_ok=hard_ok, reasons=reasons, gaps=gaps)
