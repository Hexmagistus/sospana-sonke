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
* never-checked South African companies on a known structured ATS go first.

Deliberately does NOT send the "N new jobs" candidate broadcast (same reasoning
as ``scan_due_companies``); a full deliberate sweep is the place for that.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.services.scan_service import scan_company

logger = logging.getLogger(__name__)

MIN_RESCAN_HOURS = 6.0          # a healthy company is not re-scanned sooner than this
BACKOFF_CAP_HOURS = 24.0 * 7    # a persistently failing source is retried weekly at worst
_FAST_ATS_MARKERS = ("greenhouse.io", "lever.co", "smartrecruiters.com",
                     "recruitee.com", "workable.com")


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


def select_due_company_ids(db: Session, limit: int, now: datetime | None = None) -> list[str]:
    """Pick up to `limit` companies that are due, in priority order."""
    now = now or datetime.now(timezone.utc)
    window = (db.query(Company)
              .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                      Company.careers_url.isnot(None))
              .order_by(Company.last_checked.is_(None).desc(), Company.last_checked.asc())
              .limit(max(limit * 4, 200))
              .all())
    ids = [c.id for c in window]
    fails: dict[str, int] = {}
    if ids:
        for cid, n in (db.query(VacancySource.company_id, VacancySource.consecutive_failures)
                       .filter(VacancySource.company_id.in_(ids)).all()):
            fails[cid] = max(fails.get(cid, 0), n or 0)

    due: list[Company] = []
    for c in window:
        last = _aware(c.last_checked)
        if last is None or now - last >= timedelta(hours=backoff_hours(fails.get(c.id, 0))):
            due.append(c)

    def key(c: Company):
        return (c.last_checked is not None,               # never-checked first
                (c.country or "") != "South Africa",      # SA first
                not _is_fast_ats(c.careers_url),          # structured ATS first
                _aware(c.last_checked) or datetime.min.replace(tzinfo=timezone.utc))

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
