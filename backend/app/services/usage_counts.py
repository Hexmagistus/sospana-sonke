"""Record and read anonymous daily totals.

The search total stores the filters the parser already decided: country,
category, intent, outcome, and a result-count band. It does not store the
question, a name, an email address, an IP address, or an account id. A click
total stores the employer or role id for that UTC day. Rows older than the
retention window are deleted when a total is written or when an administrator
opens the scorecard.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.usage_count import UsageClickDaily, UsageSearchDaily
from app.models.vacancy import Vacancy
from app.services.category_groups import canonical_type
from app.services.intelligence_search import IntelligenceAnswer

RETENTION_DAYS = 90
_CATEGORIES = frozenset({
    "SOE", "MUNI", "DEPT", "PRIVATE", "NGO", "UNI", "COLLEGE", "HOSPITAL",
    "SETA", "JSE", "SPORT", "FED", "MUSIC",
})
_GOVERNMENT = frozenset({"DEPT", "MUNI", "SOE"})
_INTENTS = frozenset({"roles", "employers", "both"})
_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

DEFINITIONS = {
    "search_success_rate": (
        "Searches that returned at least one stored role or employer, divided by all searches in the window."
    ),
    "not_enough_data_rate": (
        "Searches the parser could not answer from stored roles or employers, divided by all searches in the window."
    ),
    "click_through_rate": (
        "Outbound clicks in the window divided by searches that returned results. A click is not tied to a person or a question."
    ),
    "source_link_rate": (
        "Returned cards whose application or careers link starts with http or https, divided by the cards returned."
    ),
}


@dataclass(frozen=True)
class SearchCount:
    country: str
    category: str
    intent: str
    outcome: str
    result_bucket: str
    results_returned: int
    results_with_source: int


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def privacy_opt_out(request: Request) -> bool:
    """True when the browser asks not to be counted.

    Do Not Track and Global Privacy Control are the browser headers. The page
    also sends X-Privacy-Opt-Out when it can read the same signal, because a
    cross-origin request does not always carry the browser header.
    """
    dnt = (request.headers.get("dnt") or "").strip()
    gpc = (request.headers.get("sec-gpc") or "").strip()
    page = (request.headers.get("x-privacy-opt-out") or "").strip()
    return dnt == "1" or gpc == "1" or page == "1"


def _bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count <= 5:
        return "1-5"
    if count <= 20:
        return "6-20"
    if count <= 100:
        return "21-100"
    return "101+"


def _category(source_types: tuple[str, ...]) -> str:
    codes: list[str] = []
    for value in source_types:
        code = canonical_type(value)
        if code in _CATEGORIES and code not in codes:
            codes.append(code)
    if len(codes) == 1:
        return codes[0]
    if set(codes) == _GOVERNMENT:
        return "GOVERNMENT"
    return ""


def _country(value: str | None) -> str:
    text = (value or "").strip()
    if not text or len(text) > 60 or "@" in text or "://" in text:
        return ""
    return text


def _valid_source(url: str | None) -> bool:
    text = (url or "").strip().lower()
    return text.startswith("https://") or text.startswith("http://")


def classify_search(answer: IntelligenceAnswer) -> SearchCount:
    """The fields worth keeping from one answer. The question is not one of them."""
    understood = answer.understood
    unsupported = (not understood.supported) or understood.prompt
    if unsupported:
        intent = "unsupported"
        outcome = "not_enough_data"
        matched = 0
    else:
        intent = understood.looking_for if understood.looking_for in _INTENTS else "both"
        if intent == "employers":
            matched = answer.employer_count
        elif intent == "roles":
            matched = answer.vacancy_count
        else:
            matched = answer.vacancy_count if answer.vacancy_count else answer.employer_count
        outcome = "results" if matched > 0 else "empty"
    returned = 0
    with_source = 0
    if not unsupported:
        for role in answer.vacancies:
            returned += 1
            if _valid_source(role.get("application_url")):
                with_source += 1
        for employer in answer.employers:
            returned += 1
            if _valid_source(employer.get("careers_url")):
                with_source += 1
    return SearchCount(
        country=_country(understood.country),
        category=_category(tuple(understood.source_types or ())),
        intent=intent,
        outcome=outcome,
        result_bucket=_bucket(matched),
        results_returned=returned,
        results_with_source=with_source,
    )


def _purge(db: Session, today: date) -> None:
    cutoff = today - timedelta(days=RETENTION_DAYS - 1)
    db.query(UsageSearchDaily).filter(UsageSearchDaily.day < cutoff).delete(synchronize_session=False)
    db.query(UsageClickDaily).filter(UsageClickDaily.day < cutoff).delete(synchronize_session=False)


def _commit_write(db: Session, write) -> None:
    today = utc_today()
    try:
        _purge(db, today)
        write(today)
        db.commit()
    except IntegrityError:
        db.rollback()
        _purge(db, today)
        write(today)
        db.commit()


def record_search(db: Session, count: SearchCount) -> None:
    def write(today: date) -> None:
        row = (
            db.query(UsageSearchDaily)
            .filter(
                UsageSearchDaily.day == today,
                UsageSearchDaily.country == count.country,
                UsageSearchDaily.category == count.category,
                UsageSearchDaily.intent == count.intent,
                UsageSearchDaily.outcome == count.outcome,
                UsageSearchDaily.result_bucket == count.result_bucket,
            )
            .one_or_none()
        )
        if row is None:
            row = UsageSearchDaily(
                id=str(uuid.uuid4()),
                day=today,
                country=count.country,
                category=count.category,
                intent=count.intent,
                outcome=count.outcome,
                result_bucket=count.result_bucket,
                searches=0,
                results_returned=0,
                results_with_source=0,
            )
            db.add(row)
        row.searches += 1
        row.results_returned += count.results_returned
        row.results_with_source += count.results_with_source
        db.flush()

    _commit_write(db, write)


def record_click(db: Session, target: str, raw_id: str) -> None:
    if target not in {"employer", "vacancy"} or not _UUID.match(raw_id):
        raise HTTPException(status_code=422, detail="Choose an employer or a role from the results.")
    if target == "employer":
        found = db.query(Company.id).filter(Company.id == raw_id, Company.deleted_at.is_(None)).one_or_none()
    else:
        found = db.query(Vacancy.id).filter(Vacancy.id == raw_id, Vacancy.deleted_at.is_(None)).one_or_none()
    if found is None:
        raise HTTPException(status_code=422, detail="That employer or role is not in the directory.")
    target_id = found[0]

    def write(today: date) -> None:
        row = (
            db.query(UsageClickDaily)
            .filter(
                UsageClickDaily.day == today,
                UsageClickDaily.target_kind == target,
                UsageClickDaily.target_id == target_id,
            )
            .one_or_none()
        )
        if row is None:
            row = UsageClickDaily(
                id=str(uuid.uuid4()),
                day=today,
                target_kind=target,
                target_id=target_id,
                clicks=0,
            )
            db.add(row)
        row.clicks += 1
        db.flush()

    _commit_write(db, write)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _label(db: Session, kind: str, target_id: str) -> str:
    if kind == "employer":
        row = db.query(Company.company_name).filter(Company.id == target_id).one_or_none()
        return row[0] if row and row[0] else "Employer"
    row = db.query(Vacancy.title).filter(Vacancy.id == target_id).one_or_none()
    return row[0] if row and row[0] else "Role"


def scorecard(db: Session, window_days: int) -> dict:
    """Totals for the UTC window. Rates are absent when the denominator is zero."""
    days = min(max(int(window_days), 1), RETENTION_DAYS)
    today = utc_today()
    _purge(db, today)
    db.commit()
    start = today - timedelta(days=days - 1)
    searches = db.query(UsageSearchDaily).filter(UsageSearchDaily.day >= start).all()
    clicks = db.query(UsageClickDaily).filter(UsageClickDaily.day >= start).all()

    by_day: dict[date, dict] = {}
    cursor = start
    while cursor <= today:
        by_day[cursor] = {
            "day": cursor.isoformat(),
            "searches": 0,
            "searches_with_results": 0,
            "searches_empty": 0,
            "searches_not_enough_data": 0,
            "clicks": 0,
        }
        cursor += timedelta(days=1)

    total_searches = 0
    with_results = 0
    empty = 0
    not_enough = 0
    returned = 0
    sourced = 0
    for row in searches:
        total_searches += row.searches
        returned += row.results_returned
        sourced += row.results_with_source
        bucket = by_day.get(row.day)
        if bucket is None:
            continue
        bucket["searches"] += row.searches
        if row.outcome == "results":
            with_results += row.searches
            bucket["searches_with_results"] += row.searches
        elif row.outcome == "empty":
            empty += row.searches
            bucket["searches_empty"] += row.searches
        elif row.outcome == "not_enough_data":
            not_enough += row.searches
            bucket["searches_not_enough_data"] += row.searches

    total_clicks = 0
    grouped: dict[tuple[str, str], int] = {}
    for row in clicks:
        total_clicks += row.clicks
        grouped[(row.target_kind, row.target_id)] = grouped.get((row.target_kind, row.target_id), 0) + row.clicks
        bucket = by_day.get(row.day)
        if bucket is not None:
            bucket["clicks"] += row.clicks

    ranked = sorted(grouped.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))[:8]
    return {
        "window_days": days,
        "retention_days": RETENTION_DAYS,
        "counted_on": today.isoformat(),
        "searches": total_searches,
        "searches_with_results": with_results,
        "searches_empty": empty,
        "searches_not_enough_data": not_enough,
        "search_success_rate": _rate(with_results, total_searches),
        "not_enough_data_rate": _rate(not_enough, total_searches),
        "clicks": total_clicks,
        "click_through_rate": _rate(total_clicks, with_results),
        "results_returned": returned,
        "results_with_source": sourced,
        "source_link_rate": _rate(sourced, returned),
        "definitions": DEFINITIONS,
        "by_day": [by_day[day] for day in sorted(by_day)],
        "clicks_by_target": [
            {
                "target_kind": kind,
                "target_id": target_id,
                "label": _label(db, kind, target_id),
                "clicks": count,
            }
            for (kind, target_id), count in ranked
        ],
    }
