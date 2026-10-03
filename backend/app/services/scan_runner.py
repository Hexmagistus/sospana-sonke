"""Parallel, time-bounded careers scanner.

Designed to run OUTSIDE the web request path (e.g. from a GitHub Actions job
talking straight to the database), where there is no gateway timeout and a
headless browser can be installed. The API's own ``scan_due_companies`` job is
unchanged and still works for small manual/cron batches.

Why this exists: scanning companies one after another inside a single HTTP
request capped throughput at ~35 companies per 3-hour cycle, because a handful
of dead or slow sites (each up to ~20s) ate the whole time budget. Here:

* companies are scanned by a small thread pool, so slow sites overlap;
* each worker uses its own DB session (SQLAlchemy sessions are not thread-safe);
* dead/failing sources back off exponentially instead of being retried every
  cycle, so bad links stop costing time;
* healthy sources are not re-scanned more often than MIN_RESCAN_HOURS;
* due companies are ordered South Africa, then the rest of SADC, then the
  rest of Africa, then other regions. Inside a region, a supported board
  that has never been parsed successfully comes before older checks.

Deliberately does NOT send the "N new jobs" candidate broadcast (same reasoning
as ``scan_due_companies``); a full deliberate sweep is the place for that.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session, load_only

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.services.scan_service import scan_company

logger = logging.getLogger(__name__)

MIN_RESCAN_HOURS = 6.0          # a healthy HTML page is not re-scanned sooner than this
FAST_RESCAN_HOURS = 1.0         # public JSON boards (Workday, Greenhouse, …) refresh hourly
BACKOFF_CAP_HOURS = 24.0 * 7    # a persistently failing source is retried weekly at worst
_FAST_ATS_MARKERS = ("greenhouse.io", "lever.co", "smartrecruiters.com",
                     "recruitee.com", "workable.com", "myworkdayjobs.com",
                     "myworkdaysite.com", "oraclecloud.com", "breezy.hr",
                     "pinpointhq.com", "ci.hr")


def due_after_hours(url: str | None, consecutive_failures: int,
                    empty_streak: int = 0) -> float:
    """How long to wait before scanning this company again.

    Failures back off. A healthy public JSON board is due after an hour;
    a healthy HTML page waits six. A board that keeps returning no roles
    waits longer: 12 hours, then a day, then a week. That cuts traffic to
    careers pages that are consistently empty.
    """
    if consecutive_failures > 0:
        return backoff_hours(consecutive_failures)
    base = FAST_RESCAN_HOURS if _is_fast_ats(url) else MIN_RESCAN_HOURS
    streak = empty_streak or 0
    if streak >= 8:
        return max(base, 24.0 * 7)
    if streak >= 3:
        return max(base, 24.0)
    if streak >= 1:
        return max(base, 12.0)
    return base


def backoff_hours(consecutive_failures: int) -> float:
    """Minimum gap before a source with N consecutive failures is scanned again.

    0 failures -> MIN_RESCAN_HOURS; then 2h-per-failure doubling, capped at a week:
    1 -> 6h (floor), 3 -> 8h, 5 -> 32h, 7 -> 128h, 8+ -> 168h.
    """
    if consecutive_failures <= 0:
        return MIN_RESCAN_HOURS
    return min(max(MIN_RESCAN_HOURS, 2.0 ** consecutive_failures), BACKOFF_CAP_HOURS)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _is_fast_ats(url: str | None) -> bool:
    u = (url or "").lower()
    return any(m in u for m in _FAST_ATS_MARKERS)


# Directory spellings. South Africa is its own tier; the rest of SADC is next.
_SADC = frozenset({
    "Angola", "Botswana", "Comoros", "DR Congo", "Eswatini", "Lesotho",
    "Madagascar", "Malawi", "Mauritius", "Mozambique", "Namibia", "Seychelles",
    "Tanzania", "Zambia", "Zimbabwe",
})
_OTHER_AFRICA = frozenset({
    "Algeria", "Benin", "Burkina Faso", "Burundi", "Cabo Verde", "Cameroon",
    "Central African Republic", "Chad", "Congo", "Côte d'Ivoire", "Djibouti",
    "Egypt", "Equatorial Guinea", "Eritrea", "Ethiopia", "Gabon", "Gambia",
    "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Liberia", "Libya", "Mali",
    "Mauritania", "Morocco", "Niger", "Nigeria", "Rwanda", "Sao Tome and Principe",
    "Senegal", "Sierra Leone", "Somalia", "South Sudan", "Sudan", "Togo", "Tunisia",
    "Uganda",
    # Older spellings, so a row that has not been renamed still stays in Africa.
    "Cape Verde", "Ivory Coast", "Cote dIvoire", "Republic of Congo",
    "São Tomé and Príncipe",
})
_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def country_band(country: str | None) -> int:
    """0 South Africa, 1 other SADC, 2 other Africa, 3 everywhere else."""
    name = country or ""
    if name == "South Africa":
        return 0
    if name in _SADC:
        return 1
    if name in _OTHER_AFRICA:
        return 2
    return 3


def select_due_company_ids(db: Session, limit: int, now: datetime | None = None) -> list[str]:
    """Pick up to `limit` companies that are due, in priority order.

    Order is South Africa, then the rest of SADC, then the rest of Africa,
    then other regions. Inside a region, a supported board (Greenhouse, ci.hr,
    and the other fast adapters) that has never been parsed successfully
    comes first, and the oldest check comes first after that. The scan's
    time budget is unchanged: this only chooses who is in the batch.

    The choice is read from the whole due set. An earlier version only looked
    at the 200 oldest checks, so a ci.hr board the URL tester had already
    touched waited behind every never-checked HTML page.
    """
    now = now or datetime.now(timezone.utc)
    companies = (db.query(Company)
                 .options(load_only(Company.id, Company.country, Company.careers_url,
                                    Company.last_checked))
                 .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                         Company.careers_url.isnot(None))
                 .all())
    fails: dict[str, int] = {}
    streaks: dict[str, int] = {}
    parsed: set[str] = set()
    for cid, n, streak, success_at in (
        db.query(VacancySource.company_id, VacancySource.consecutive_failures,
                 VacancySource.empty_streak, VacancySource.last_success_at)
        .all()
    ):
        fails[cid] = max(fails.get(cid, 0), n or 0)
        streaks[cid] = max(streaks.get(cid, 0), streak or 0)
        if success_at is not None:
            parsed.add(cid)

    due: list[Company] = []
    for c in companies:
        last = _aware(c.last_checked)
        gap = due_after_hours(c.careers_url, fails.get(c.id, 0), streaks.get(c.id, 0))
        if last is None or now - last >= timedelta(hours=gap):
            due.append(c)

    def key(c: Company):
        last = _aware(c.last_checked)
        unparsed_adapter = c.id not in parsed and _is_fast_ats(c.careers_url)
        return (country_band(c.country),
                0 if unparsed_adapter else 1,
                last is not None,
                last or _EPOCH,
                c.id)

    due.sort(key=key)
    return [c.id for c in due[:limit]]


def _stamp_failure(db: Session, company_id: str, now: datetime) -> None:
    """A scan raised before scan_source could record anything: still stamp the company
    and bump its source's failure counter so back-off grows and it isn't retried at once."""
    db.rollback()
    company = db.get(Company, company_id)
    if company is None:
        return
    company.last_checked = now
    for src in db.query(VacancySource).filter(VacancySource.company_id == company_id).all():
        src.consecutive_failures = (src.consecutive_failures or 0) + 1
    db.commit()


def scan_due_parallel(session_factory: Callable[[], Session], limit: int = 400,
                      max_seconds: float = 2400.0, workers: int = 8,
                      scan_fn=scan_company, now: datetime | None = None) -> dict:
    """Scan due companies concurrently until `limit` or `max_seconds` is reached.

    In-flight scans are allowed to finish (each is bounded by its own HTTP timeouts);
    no new scan starts after the deadline.
    """
    started = time.monotonic()
    now = now or datetime.now(timezone.utc)
    with session_factory() as db:
        ids = select_due_company_ids(db, limit, now)

    def work(company_id: str) -> dict | None:
        if time.monotonic() - started > max_seconds:
            return None                                   # deadline: don't start
        out = {"created": 0, "failed": 0, "new_ids": []}
        with session_factory() as db:
            try:
                company = db.get(Company, company_id)
                if company is None:
                    return out
                reports = scan_fn(db, company)
                out["created"] = sum(r.created for r in reports)
                out["failed"] = sum(1 for r in reports if r.status not in ("ok", "empty"))
                for r in reports:
                    out["new_ids"].extend(r.created_vacancy_ids)
                company.last_checked = now
                db.commit()
            except Exception:
                logger.warning("scan_due_parallel: failed to scan company %s", company_id,
                               exc_info=True)
                out["failed"] += 1
                try:
                    _stamp_failure(db, company_id, now)
                except Exception:
                    logger.warning("scan_due_parallel: could not stamp failure for %s",
                                   company_id, exc_info=True)
        return out

    scanned = created = failed = 0
    new_ids: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for fut in as_completed([pool.submit(work, cid) for cid in ids]):
            res = fut.result()
            if res is None:
                continue
            scanned += 1
            created += res["created"]
            failed += res["failed"]
            new_ids.extend(res["new_ids"])
    return {"due_selected": len(ids), "companies_scanned": scanned,
            "vacancies_created": created, "sources_failed": failed,
            "stopped_early_on_time_budget": scanned < len(ids),
            "elapsed_seconds": round(time.monotonic() - started, 1)}
