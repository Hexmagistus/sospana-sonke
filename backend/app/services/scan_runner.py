"""Parallel, time-bounded careers scanner.

Designed to run OUTSIDE the web request path (e.g. from a GitHub Actions job
talking straight to the database), where there is no gateway timeout and a
headless browser can be installed (scripts/run_scan.py). The queue order,
back-off and claims defined here are shared with the API's own
``scan_due_companies`` cron job, which runs app.services.scan_batch.

Why this exists: scanning companies one after another inside a single HTTP
request capped throughput at ~35 companies per 3-hour cycle, because a handful
of dead or slow sites (each up to ~20s) ate the whole time budget. Here:

* companies are scanned by a small thread pool, so slow sites overlap;
* each worker uses its own DB session (SQLAlchemy sessions are not thread-safe);
* dead/failing sources back off exponentially instead of being retried every
  cycle, so bad links stop costing time;
* healthy sources are not re-scanned more often than MIN_RESCAN_HOURS;
* due sources are ordered never-scanned first, then by the oldest scan, with
  South Africa, the rest of SADC and the rest of Africa given a bounded head
  start (BAND_LEAD_HOURS) so no region is starved; see select_due.

Deliberately does NOT send the "N new jobs" candidate broadcast (same reasoning
as ``scan_due_companies``); a full deliberate sweep is the place for that.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Callable

from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.orm import Session, load_only

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.scraper.errors import NEEDS_REVIEW_AFTER, is_permanent
from app.services.scan_service import scan_company

logger = logging.getLogger(__name__)

MIN_RESCAN_HOURS = 6.0          # a healthy HTML page is not re-scanned sooner than this
FAST_RESCAN_HOURS = 1.0         # public JSON boards (Workday, Greenhouse, …) refresh hourly
BACKOFF_CAP_HOURS = 24.0 * 7    # a persistently failing source is retried weekly at worst
_FAST_ATS_MARKERS = ("greenhouse.io", "lever.co", "smartrecruiters.com",
                     "recruitee.com", "workable.com", "myworkdayjobs.com",
                     "myworkdaysite.com", "oraclecloud.com", "breezy.hr",
                     "pinpointhq.com", "ci.hr")


TRANSIENT_BACKOFF_CAP_HOURS = 72.0   # timeouts, 5xx, 403/429: still tried twice a week
# Not failures, but asking again soon gets the same answer.
STATUS_RECHECK_HOURS = {
    "robots_disallowed": 24.0 * 7,
    "javascript_required": 24.0 * 7,
    "blocked": 72.0,
}


def due_after_hours(url: str | None, consecutive_failures: int,
                    empty_streak: int = 0, error_category: str | None = None,
                    last_status: str | None = None) -> float:
    """How long to wait before scanning this company again.

    Failures back off (by kind, see backoff_hours). A healthy public JSON
    board is due after an hour; a healthy HTML page waits six. A board that
    keeps returning no roles waits longer: 12 hours, then a day, then a week.
    A robots.txt refusal or a page that needs a browser is asked again
    weekly, a bot challenge after three days.

    These gaps are only a floor. The queue itself is ordered by the oldest
    scan (select_due), so a recently scanned source is never picked ahead of
    one that has waited longer.
    """
    if consecutive_failures > 0:
        return backoff_hours(consecutive_failures, error_category)
    if last_status in STATUS_RECHECK_HOURS:
        return STATUS_RECHECK_HOURS[last_status]
    base = FAST_RESCAN_HOURS if _is_fast_ats(url) else MIN_RESCAN_HOURS
    streak = empty_streak or 0
    if streak >= 8:
        return max(base, 24.0 * 7)
    if streak >= 3:
        return max(base, 24.0)
    if streak >= 1:
        return max(base, 12.0)
    return base


def backoff_hours(consecutive_failures: int, error_category: str | None = None) -> float:
    """Minimum gap before a source with N consecutive failures is scanned again.

    Without a category (older rows): 2h-per-failure doubling, floor
    MIN_RESCAN_HOURS, cap a week: 1 -> 6h, 3 -> 8h, 5 -> 32h, 7 -> 128h, 8+ -> 168h.

    Permanent failures (404, DNS, invalid URL, broken certificate) do not fix
    themselves between scans: 1 -> 24h, 2 -> 72h, 3+ -> a week (the source is
    NEEDS_REVIEW by then). Transient ones (timeout, connection reset, 5xx,
    403/429) follow the doubling but are capped at three days.
    """
    if consecutive_failures <= 0:
        return MIN_RESCAN_HOURS
    if is_permanent(error_category):
        if consecutive_failures >= NEEDS_REVIEW_AFTER:
            return BACKOFF_CAP_HOURS
        return 24.0 if consecutive_failures == 1 else 72.0
    hours = min(max(MIN_RESCAN_HOURS, 2.0 ** consecutive_failures), BACKOFF_CAP_HOURS)
    if error_category:
        hours = min(hours, TRANSIENT_BACKOFF_CAP_HOURS)
    return hours


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


# How much "older" a region's sources count when the queue is sorted. South
# Africa goes first, then the rest of SADC, the rest of Africa, then other
# regions, but only by this many hours: a source elsewhere that has waited a
# day and a half longer still comes first, so no region is starved.
BAND_LEAD_HOURS = {0: 36.0, 1: 24.0, 2: 12.0, 3: 0.0}
UNPARSED_BOARD_LEAD_HOURS = 24.0
SLOW_SOURCE_MS = 4500


@dataclass(frozen=True)
class DueItem:
    company_id: str
    source_id: str | None      # None: no source row yet, so never scanned
    last_scanned: datetime | None
    band: int
    url: str
    # last_checked exactly as read from the database, for claim_source's
    # compare-and-set (SQLite hands back naive datetimes).
    claim_token: datetime | None = None
    # Took SLOW_SOURCE_MS or more last time, or timed out: fetched with the
    # longer read timeout (scan_batch) so a slow but working site is not lost.
    slow: bool = False


def select_due(db: Session, limit: int, now: datetime | None = None) -> list[DueItem]:
    """Up to `limit` due sources, the most overdue first.

    "When was this scanned" is the vacancy source's own last_checked. The
    company's last_checked is also stamped by the daily URL health check
    (test_all_urls), so using it made a company look freshly scanned when
    only its link had been pinged.

    Order: never scanned first (South Africa, SADC, Africa, others; inside a
    region a supported board before plain HTML), then by the oldest scan,
    where each region gets the head start in BAND_LEAD_HOURS and a board that
    has never parsed successfully another UNPARSED_BOARD_LEAD_HOURS.
    The old order put every due South African source ahead of any other
    region; with six-hour rescans that kept re-scanning the same South
    African pages while 60% of sources went a week without a check.
    Disabled sources are skipped.
    """
    now = now or datetime.now(timezone.utc)
    companies = (db.query(Company)
                 .options(load_only(Company.id, Company.country, Company.careers_url))
                 .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                         Company.careers_url.isnot(None))
                 .all())
    sources: dict[str, tuple] = {}
    for row in (db.query(VacancySource.company_id, VacancySource.id, VacancySource.last_checked,
                         VacancySource.consecutive_failures, VacancySource.empty_streak,
                         VacancySource.error_category, VacancySource.last_status,
                         VacancySource.active, VacancySource.created_at,
                         VacancySource.last_success_at, VacancySource.response_time_ms)
                .order_by(VacancySource.created_at.asc(), VacancySource.id.asc())
                .all()):
        # scan_company scans the company's first source; mirror that.
        sources.setdefault(row[0], row)

    due: list[tuple] = []
    for c in companies:
        row = sources.get(c.id)
        if row is not None and row[7] is False:
            continue
        last = _aware(row[2]) if row is not None else None
        band = country_band(c.country)
        if last is not None:
            gap = due_after_hours(c.careers_url, row[3] or 0, row[4] or 0, row[5], row[6])
            if now - last < timedelta(hours=gap):
                continue
        item = DueItem(company_id=c.id, source_id=row[1] if row is not None else None,
                       last_scanned=last, band=band, url=c.careers_url or "",
                       claim_token=row[2] if row is not None else None,
                       slow=_is_slow(row))
        # A supported board (Greenhouse, ci.hr, ...) that has never parsed
        # successfully goes ahead of plain HTML pages: first inside its
        # region when never scanned, otherwise with UNPARSED_BOARD_LEAD_HOURS.
        unparsed_board = _is_fast_ats(c.careers_url) and (row is None or row[9] is None)
        if last is None:
            key = (0, band, 0 if unparsed_board else 1, _EPOCH, c.id)
        else:
            lead = BAND_LEAD_HOURS[band] + (UNPARSED_BOARD_LEAD_HOURS if unparsed_board else 0.0)
            key = (1, 0, 0, last - timedelta(hours=lead), c.id)
        due.append((key, item))
    due.sort(key=lambda kv: kv[0])
    return [item for _, item in due[:limit]]


def _is_slow(row) -> bool:
    """Fetch with the longer read timeout? (row from select_due's source query)

    Yes after a slow answer (SLOW_SOURCE_MS or more) or a timeout, so a slow
    but working site is read on the next try. Not once a source has timed
    out twice in a row: that host is most likely dead, and the long timeout
    would only cost time.
    """
    if row is None:
        return False
    fails, category, elapsed_ms = row[3] or 0, row[5], row[10] or 0
    if category == "TIMEOUT" and fails >= 2:
        return False
    return elapsed_ms >= SLOW_SOURCE_MS or category == "TIMEOUT"


def select_due_company_ids(db: Session, limit: int, now: datetime | None = None) -> list[str]:
    """Company ids of select_due, in the same order."""
    return [item.company_id for item in select_due(db, limit, now)]


def claim_source(db: Session, source_id: str, previous: datetime | None, now: datetime) -> bool:
    """Stamp a source as being scanned, unless someone else already did.

    Compare-and-set on last_checked: only succeeds if nobody stamped the row
    after we read it (still NULL, or not newer than the value we read). Two
    overlapping cron calls (the GitHub workflow and cron-job.org both call
    this job) therefore never scan the same source twice; the loser skips it
    and moves on. "Not newer" rather than "equal" so a value written by
    another tool with a different precision still matches on SQLite.
    """
    cond = (VacancySource.last_checked.is_(None) if previous is None
            else VacancySource.last_checked <= previous)
    res = db.execute(update(VacancySource)
                     .where(VacancySource.id == source_id, cond)
                     .values(last_checked=now)
                     .execution_options(synchronize_session=False))
    db.commit()
    return (res.rowcount or 0) == 1


def release_claim(db: Session, source_id: str, claimed_at: datetime,
                  previous: datetime | None) -> None:
    """Put back the old last_checked of a source we claimed but did not scan
    (the run ran out of time), so it keeps its place at the front of the queue."""
    db.execute(update(VacancySource)
               .where(VacancySource.id == source_id, VacancySource.last_checked == claimed_at)
               .values(last_checked=previous)
               .execution_options(synchronize_session=False))
    db.commit()


def release_claims(db: Session, items: list[tuple[str, datetime | None]],
                   claimed_at: datetime) -> None:
    """release_claim for several sources, in one transaction (one commit)."""
    for source_id, previous in items:
        db.execute(update(VacancySource)
                   .where(VacancySource.id == source_id, VacancySource.last_checked == claimed_at)
                   .values(last_checked=previous)
                   .execution_options(synchronize_session=False))
    db.commit()


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
