"""Map form fields to TRUTHFUL profile values (blueprint section 15).

Only fills a field when the candidate's profile supports the answer. Fields it
cannot map that are marked required become `unknown_required`, which forces the
engine to hand back to the candidate rather than guess.
"""
from __future__ import annotations

import re

from app.automation.base import FormFieldSpec, SubmissionPlan

# (regex over field name+label) -> canonical answer key
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"e-?mail", re.I), "email"),
    (re.compile(r"first ?name|given", re.I), "first_name"),
    (re.compile(r"last ?name|surname|family", re.I), "last_name"),
    (re.compile(r"full ?name|^name$|your name|applicant name", re.I), "full_name"),
    (re.compile(r"phone|mobile|cell|contact number", re.I), "phone"),
    (re.compile(r"years.*experience|experience.*years|yrs", re.I), "years_experience"),
    (re.compile(r"salary|expected.*remuneration|ctc", re.I), "min_salary"),
    (re.compile(r"driver.?s? licen", re.I), "drivers_licence"),
    (re.compile(r"work aut|right to work|legally.*work|citizenship", re.I), "work_authorization"),
    (re.compile(r"city|town|location", re.I), "city"),
    (re.compile(r"linkedin", re.I), "linkedin_url"),
    (re.compile(r"current (role|position|occupation|title)", re.I), "current_occupation"),
]


def build_answer_map(facts: dict) -> dict[str, str]:
    name = (facts.get("full_name") or "").split()
    out: dict[str, str] = {}

    def put(k, v):
        if v not in (None, "", []):
            out[k] = str(v)

    put("email", facts.get("email"))
    put("phone", facts.get("phone"))
    put("full_name", facts.get("full_name"))
    put("first_name", name[0] if name else None)
    put("last_name", " ".join(name[1:]) if len(name) > 1 else None)
    put("years_experience", facts.get("years_experience"))
    put("min_salary", facts.get("minimum_salary"))
    put("city", facts.get("city"))
    put("linkedin_url", facts.get("linkedin_url"))
    put("current_occupation", facts.get("current_occupation"))
    put("work_authorization", facts.get("work_authorization"))
    if facts.get("drivers_licence"):
        out["drivers_licence"] = "Yes"
    return out


def plan_submission(fields: list[FormFieldSpec], answer_map: dict[str, str]) -> SubmissionPlan:
    plan = SubmissionPlan()
    for f in fields:
        if f.input_type in ("password", "file", "checkbox", "radio"):
            # password/file are handled as blockers upstream; skip choice inputs.
            continue
        # Normalise separators so "full_name"/"first-name" match word patterns.
        haystack = re.sub(r"[_\-]+", " ", f"{f.name} {f.label or ''}")
        key = next((k for pat, k in _PATTERNS if pat.search(haystack)), None)
        if key and key in answer_map:
            plan.values[f.name] = answer_map[key]
        elif f.required:
            plan.unknown_required.append(f.label or f.name)
    return plan
