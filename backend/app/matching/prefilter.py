"""Cheap deterministic pre-filter (blueprint sections 8, 16, 30 & 37).

Runs BEFORE any scoring/AI to cheaply discard vacancies the candidate has ruled
out — excluded companies/roles and a salary floor. Keeping this cheap and first is
central to the cost model: only survivors are scored.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PreFilterOutcome:
    passes: bool
    reason: str | None = None


def prefilter(*, vacancy_title: str, company_name: str, vacancy_salary: int | None,
              excluded_companies: set[str], excluded_roles: set[str],
              minimum_salary: int | None) -> PreFilterOutcome:
    title = (vacancy_title or "").lower()
    company = (company_name or "").lower()

    if company and any(ex and ex in company for ex in excluded_companies):
        return PreFilterOutcome(False, "Company is on your excluded list.")
    if any(ex and ex in title for ex in excluded_roles):
        return PreFilterOutcome(False, "Role matches one of your excluded role keywords.")
    if minimum_salary and vacancy_salary and vacancy_salary < minimum_salary:
        return PreFilterOutcome(False, f"Advertised salary is below your minimum (R{minimum_salary}).")
    return PreFilterOutcome(True)
