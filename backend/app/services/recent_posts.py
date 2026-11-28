"""Ordering helpers for "recently posted" open roles.

A role's recency day is the employer's stated ``posting_date`` when the advert
gives one, otherwise the day our scanner first stored it (``first_seen_at``).
Ties on the same day follow the standing country order: South Africa, the rest
of SADC, the rest of Africa, then other regions.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import case, func

from app.models.company import Company
from app.models.vacancy import Vacancy
from app.services.scan_runner import _OTHER_AFRICA, _SADC

RECENT_SORTS = frozenset({"recent", "newest"})


def recent_day_expr():
    """SQL: posting day, else the first-seen day (both portable to SQLite)."""
    return func.coalesce(Vacancy.posting_date, func.date(Vacancy.first_seen_at))


def region_band_rank():
    """0 South Africa, 1 rest of SADC, 2 rest of Africa, 3 elsewhere (role country, else employer)."""
    where = func.coalesce(func.nullif(Vacancy.country, ""), Company.country)
    return case(
        (where == "South Africa", 0),
        (where.in_(sorted(_SADC)), 1),
        (where.in_(sorted(_OTHER_AFRICA)), 2),
        else_=3,
    )


def _band(name: str | None) -> int:
    if name == "South Africa":
        return 0
    if name in _SADC:
        return 1
    if name in _OTHER_AFRICA:
        return 2
    return 3


def _iso_day(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")[:10]


def sort_recent(jobs: list[dict]) -> list[dict]:
    """Python twin of the SQL order, for the offline snapshot (newest first)."""
    out = sorted(jobs, key=lambda j: str(j.get("id") or ""))
    out.sort(key=lambda j: _band(j.get("country") or j.get("company_country")))
    out.sort(key=lambda j: str(j.get("first_seen_at") or ""), reverse=True)
    out.sort(key=lambda j: _iso_day(j.get("posting_date") or j.get("first_seen_at")), reverse=True)
    return out
