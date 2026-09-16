"""Gap analysis: "Why am I not matching?" (product brief's named differentiator).

Turns a candidate/vacancy pair into a "what you already have / what you're
missing / suggested next steps" view. This deliberately does NOT re-implement or
second-guess the matching engine's own judgement — it calls the exact same
deterministic `requirement_met()` function on the exact same hard requirements
the engine scored, so a candidate's gap analysis is always consistent with their
match score and reasons. No LLM, no invented qualifications: every "have"/
"missing" line is one requirement's own text, verbatim, from the vacancy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.matching.engine import CandidateData, VacancyData, requirement_met


@dataclass
class GapItem:
    text: str
    category: str


@dataclass
class PathwayStep:
    step: str
    category: str


@dataclass
class GapAnalysis:
    # None (not 0) when there's nothing assessable at all -- distinct from "you
    # meet 0% of what could be checked".
    percent_requirements_met: float | None
    have: list[GapItem] = field(default_factory=list)
    missing: list[GapItem] = field(default_factory=list)
    # Requirements the engine itself couldn't judge from the candidate's profile
    # (e.g. no stated skills at all) -- shown honestly as "add this to your
    # profile to find out", never silently counted as met or missing.
    unclear: list[GapItem] = field(default_factory=list)
    pathway: list[PathwayStep] = field(default_factory=list)


_PATHWAY_TEMPLATES = {
    "qualification": "Work toward the qualification this role asks for: {text}",
    "certification": "Complete this certification: {text}",
    "registration": "Obtain this professional registration: {text}",
    "licence": "Obtain the required licence: {text}",
    "experience": "Build up the required experience: {text}",
    "skill": "Develop this skill: {text}",
    "other": "Address this requirement: {text}",
}


def build_gap_analysis(cand: CandidateData, vac: VacancyData) -> GapAnalysis:
    hard_reqs = [r for r in vac.requirements if r.get("kind") == "hard"]
    have: list[GapItem] = []
    missing: list[GapItem] = []
    unclear: list[GapItem] = []

    for r in hard_reqs:
        result = requirement_met(cand, r)
        item = GapItem(text=r["text"], category=r.get("category", "other"))
        if result is True:
            have.append(item)
        elif result is False:
            missing.append(item)
        else:
            unclear.append(item)

    assessable = len(have) + len(missing)
    percent = round((len(have) / assessable) * 100.0) if assessable else None

    pathway = [
        PathwayStep(
            step=_PATHWAY_TEMPLATES.get(m.category, _PATHWAY_TEMPLATES["other"]).format(text=m.text),
            category=m.category,
        )
        for m in missing
    ]

    return GapAnalysis(percent_requirements_met=percent, have=have, missing=missing,
                       unclear=unclear, pathway=pathway)
