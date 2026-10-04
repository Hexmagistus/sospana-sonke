"""Recurring job functions (blueprint section 22).

Each job is a plain function of a DB session so it can be invoked by any scheduler
(APScheduler / Celery beat / cron in production) or triggered manually by an admin.
Jobs are deterministic and safe to re-run.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone

import httpx

from sqlalchemy.orm import Session

from app.core.config import settings

from app.models.company import Company
from app.models.vacancy import Vacancy
from app.services.scan_service import scan_company

logger = logging.getLogger(__name__)


def _alert_candidates_of_new_jobs(db: Session, new_vacancy_ids: list[str], job_run_id: str | None) -> int:
    """Broad "new jobs" alert for a scan run — a no-op if the run has no id to key
    idempotency on (e.g. called outside the job runner) or found nothing new."""
    if not job_run_id or not new_vacancy_ids:
        return 0
    from app.services.notification_service import notify_new_jobs_broadcast
    sent = notify_new_jobs_broadcast(db, vacancy_ids=new_vacancy_ids, job_run_id=job_run_id)
    db.commit()
    return sent


def scan_all_companies(db: Session, job_run_id: str | None = None, country: str | None = None) -> dict:
    """Scan every active company that has a careers URL. Returns a summary.

    country: when given, restrict the sweep to that country only (e.g. "South Africa").
    """
    query = (db.query(Company)
             .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                     Company.careers_url.isnot(None)))
    if country:
        query = query.filter(Company.country == country)
    companies = query.all()
    scanned = created = failed = 0
    new_vacancy_ids: list[str] = []
    for company in companies:
        try:
            reports = scan_company(db, company)
            scanned += 1
            created += sum(r.created for r in reports)
            failed += sum(1 for r in reports if r.status not in ("ok", "empty"))
            for r in reports:
                new_vacancy_ids.extend(r.created_vacancy_ids)
        except Exception:
            logger.warning("scan_all_companies: failed to scan %s (%s)",
                           company.company_name, company.id, exc_info=True)
            failed += 1
    candidates_alerted = _alert_candidates_of_new_jobs(db, new_vacancy_ids, job_run_id)
    return {"companies_scanned": scanned, "vacancies_created": created, "sources_failed": failed,
            "candidates_alerted": candidates_alerted}


def scan_south_africa(db: Session, job_run_id: str | None = None) -> dict:
    """Scan every active South African company with a careers URL.

    A scoped entry point for the current rollout phase (South Africa first) that
    reuses scan_all_companies's logic and change-detection/alerting behaviour.
    """
    return scan_all_companies(db, job_run_id=job_run_id, country="South Africa")


def scan_due_companies(db: Session, limit: int = 40, job_run_id: str | None = None,
                       max_seconds: float = 55.0) -> dict:
    """Scan the next due batch, then stamp them so the next run moves on.

    Who is due is chosen by select_due_company_ids: South Africa, then the
    rest of SADC, then the rest of Africa, then other regions. Inside a
    region, a supported board that has never been parsed successfully
    (including ci.hr) comes before the oldest check. The wall-clock budget
    below is what keeps a run inside the free-tier gateway.

    Keeps each run bounded (a few minutes, not hours) so a free external
    scheduler can call it reliably every few hours; the whole database still
    cycles through in under a week rather than 15+ days.

    Batch size ALONE turned out not to bound the run's wall-clock time: 25
    companies took ~1.5 min, but the "due" batch is dominated by companies
    that have NEVER been checked -- many of those URLs are slow, unreachable
    or block robots.txt, and each one can burn close to the full per-request
    timeout (robots.txt + page fetch, ~10s each -> up to ~20s of dead weight
    per bad company) before scan_service gives up on it. limit=100 hit an
    HTTP 502 at 9m13s and limit=50 still took 7m53s -- both cut off by
    Render's free-tier gateway before finishing, because a handful of slow
    companies dominated the batch regardless of its size.

    So this now bails out of the loop once max_seconds of wall-clock time has
    passed, whatever count it has reached -- every run is bounded by TIME, not
    by how many of the batch happen to be slow, so it always returns well
    inside the calling workflow's timeout (curl --max-time 100). A company is
    not started unless about 20 seconds remain, HTTP retries are capped at one
    attempt, and each request times out at 8 seconds. That keeps one dead host
    from running past the workflow limit after the loop has already decided
    there is time left. limit is now just an upper cap for a lucky all-fast
    batch, not the throttle.

    The scan uses the request's single DB session (one checkout from the
    pool of 5 + 2 overflow). It does not open a thread pool of sessions, so
    user requests still have connections left.

    Deliberately skips the "N new jobs" candidate broadcast that
    scan_all_companies/scan_south_africa send: NOTIFY_EMAILS is on in
    production, and notify_new_jobs_broadcast emails every active candidate
    synchronously, one HTTP call per candidate, inside this same request --
    with even a couple hundred candidates that alone can run minutes past the
    scan loop's own time budget (this is what was actually causing runs to
    blow well past 240s even after the loop itself was bounded). A partial
    rotating batch finding a handful of jobs every 3 hours isn't the right
    trigger for a mass email anyway; a full/manual sweep (scan_all_companies)
    is a more sensible place for that broadcast.
    """
    # Same priority as the parallel runner. Failing URLs still back off.
    from app.services.scan_runner import _stamp_failure, select_due_company_ids
    now = datetime.now(timezone.utc)
    ids = select_due_company_ids(db, limit, now)
    companies = [c for cid in ids if (c := db.get(Company, cid)) is not None]
    scanned = created = failed = 0
    new_vacancy_ids: list[str] = []
    started = time.monotonic()
    timed_out = False
    # Don't begin a company that cannot finish inside the remaining budget.
    # robots.txt + one page, one attempt each, 8s timeout, plus a little slack.
    _MIN_START_SECONDS = 20.0
    from app.scraper.politeness import backoff_retry_cap
    client = httpx.Client(
        timeout=httpx.Timeout(8.0, connect=5.0),
        follow_redirects=True,
        headers={"User-Agent": settings.URL_TEST_USER_AGENT},
    )
    try:
        with backoff_retry_cap(1):
            for company in companies:
                if max_seconds - (time.monotonic() - started) < _MIN_START_SECONDS:
                    timed_out = True
                    break
                company_id = company.id
                company_name = company.company_name
                try:
                    reports = scan_company(db, company, client=client)
                    scanned += 1
                    created += sum(r.created for r in reports)
                    failed += sum(1 for r in reports if r.status not in ("ok", "empty"))
                    for r in reports:
                        new_vacancy_ids.extend(r.created_vacancy_ids)
                    company.last_checked = now
                    db.add(company)
                    db.commit()
                except Exception:
                    # A failed INSERT aborts the transaction. Reading the company
                    # after that, or committing it, raises again and the cron
                    # returns a bare 500. Roll back, stamp last_checked, continue.
                    logger.warning("scan_due_companies: failed to scan %s (%s)",
                                   company_name, company_id, exc_info=True)
                    failed += 1
                    try:
                        _stamp_failure(db, company_id, now)
                    except Exception:
                        logger.warning(
                            "scan_due_companies: could not stamp failure for %s",
                            company_id, exc_info=True,
                        )
                        db.rollback()
    finally:
        client.close()
    # No candidate broadcast here -- see the docstring; it's the one uncapped,
    # potentially-per-candidate-email step and doesn't belong in a job whose
    # whole point is to return within a tight time budget every few hours.
    return {"batch_limit": limit, "companies_scanned": scanned,
            "vacancies_created": created, "sources_failed": failed,
            "candidates_alerted": 0, "stopped_early_on_time_budget": timed_out}


def check_link_changes(db: Session, limit: int = 25, job_run_id: str | None = None) -> dict:
    """Hash-check the careers pages checked longest ago and alert any
    CompanyWatch subscribers when a page's content changed since last time.

    A companion to scan_due_companies for the many companies/universities
    whose careers link is a homepage or news feed rather than a structured
    job board -- app/scraper can't extract individual vacancies from those,
    so this gives them a cheaper "did anything change" signal instead. Same
    rotating-batch shape so a free external cron can call it often and the
    whole database still cycles through over time.
    """
    from app.services.link_check_service import check_company_content, notify_watchers_of_change, make_client

    companies = (db.query(Company)
                 .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                         Company.careers_url.isnot(None))
                 # NULL content_checked_at (never checked) first, then oldest.
                 .order_by(Company.content_checked_at.is_(None).desc(),
                           Company.content_checked_at.asc())
                 .limit(limit)
                 .all())

    checked = changed_count = notified = errors = 0
    client = make_client()
    try:
        for company in companies:
            try:
                did_change = check_company_content(company, client=client)
                checked += 1
                if did_change:
                    changed_count += 1
                    notified += notify_watchers_of_change(db, company)
                db.add(company)
                db.commit()
            except Exception:
                logger.warning("check_link_changes: failed to check %s (%s)",
                               company.company_name, company.id, exc_info=True)
                errors += 1
                db.rollback()
    finally:
        client.close()

    return {"batch_limit": limit, "companies_checked": checked,
            "pages_changed": changed_count, "watchers_notified": notified, "errors": errors}


def discover_company_icons(db: Session, limit: int = 12, job_run_id: str | None = None,
                           max_seconds: float = 40.0) -> dict:
    """Fetch each company's own icon ONCE and store it in our database.

    This is the only place icons are fetched from the web, and never on a page
    view. Polite by design: robots.txt is honoured, requests to the same host
    are spaced out, a small batch per run, a wall-clock budget, a descriptive
    User-Agent, size/type-checked responses, and a "nothing found" result is
    stored too (retried after 30 days) so nobody is asked repeatedly.

    Order is South Africa, the rest of SADC, the rest of Africa, then others;
    never-checked companies first. Companies with no usable source (no website,
    ATS-only careers link) are stamped without any request: the monogram badge
    is their icon. Rows that pre-date stored bytes (a URL only) are converted
    after 7 days instead of 30 so existing icons stop being hot-linked soon.
    """
    from sqlalchemy import and_, case, or_
    from datetime import timedelta
    from app.scraper.politeness import RateLimiter, RobotsChecker
    from app.services.logo_service import fetch_company_icon, has_icon_source
    from app.services.scan_runner import _OTHER_AFRICA, _SADC

    now = datetime.now(timezone.utc)
    miss_cutoff = now - timedelta(days=30)
    legacy_cutoff = now - timedelta(days=7)
    has_url = and_(Company.favicon_url.isnot(None), Company.favicon_url != "")
    band = case(
        (Company.country == "South Africa", 0),
        (Company.country.in_(sorted(_SADC)), 1),
        (Company.country.in_(sorted(_OTHER_AFRICA)), 2),
        else_=3,
    )
    pool = (db.query(Company)
            .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                    Company.favicon_data.is_(None),
                    or_(Company.favicon_checked_at.is_(None),
                        and_(has_url, Company.favicon_checked_at < legacy_cutoff),
                        and_(~has_url, Company.favicon_checked_at < miss_cutoff)))
            .order_by(band, Company.favicon_checked_at.is_(None).desc(),
                      Company.favicon_checked_at.asc(), Company.company_name)
            .limit(limit * 10)
            .all())

    stored = missed = skipped = attempted = 0
    started = time.monotonic()
    timed_out = False
    client = httpx.Client(
        timeout=httpx.Timeout(8.0, connect=5.0),
        follow_redirects=True,
        headers={"User-Agent": settings.URL_TEST_USER_AGENT},
    )
    robots = RobotsChecker(client)
    limiter = RateLimiter(min_interval_seconds=1.0)
    try:
        for company in pool:
            if attempted >= limit:
                break
            if max_seconds - (time.monotonic() - started) < 15.0:
                timed_out = True
                break
            name = company.company_name
            try:
                if not has_icon_source(company.official_website, company.careers_url,
                                       company.favicon_url or None):
                    company.favicon_checked_at = now
                    skipped += 1
                else:
                    attempted += 1
                    found = fetch_company_icon(
                        company.official_website, company.careers_url,
                        client, robots, limiter, known_icon_url=company.favicon_url or None)
                    company.favicon_checked_at = datetime.now(timezone.utc)
                    if found:
                        company.favicon_url = found.source_url
                        company.favicon_data = found.data
                        company.favicon_mime = found.mime
                        stored += 1
                    else:
                        missed += 1  # keep any legacy URL; the monogram covers a true miss
                db.add(company)
                db.commit()
            except Exception:
                logger.warning("discover_company_icons: failed for %s", name, exc_info=True)
                db.rollback()
    finally:
        client.close()
    return {"batch_limit": limit, "icons_stored": stored, "nothing_found": missed,
            "no_source_monogram_only": skipped, "stopped_early_on_time_budget": timed_out}


def close_expired_vacancies(db: Session, job_run_id: str | None = None) -> dict:
    """Close every open vacancy whose own advertised closing date has passed.

    A scan closes a role only after it has been missing from two successful
    non-empty scans (scan_service.scan_source never wipes vacancies on an
    empty or failed fetch), so a role can otherwise sit "open"
    for days past its own closing date just because the company's careers
    page hasn't been re-scanned yet. This is a pure DB sweep -- no network
    calls -- so it keeps is_open accurate everywhere that filters on it
    (listings) without waiting on the scan rotation, and always
    finishes well within any scheduler's timeout.
    """
    today = date.today()
    stale = (db.query(Vacancy)
             .filter(Vacancy.is_open.is_(True), Vacancy.closing_date.isnot(None),
                     Vacancy.closing_date < today)
             .all())
    for vac in stale:
        vac.is_open = False
        vac.lifecycle_status = "EXPIRED"
    db.commit()
    return {"vacancies_closed": len(stale)}


DISABLED_MATCHING = {
    "status": "disabled",
    "detail": "Job matching has been removed; this job does nothing. "
              "(Kept so an external scheduler that still calls it gets a harmless 200.)",
}


def match_all_candidates(db: Session, job_run_id: str | None = None) -> dict:
    """Retired. Job matching was removed (it kept matching old posts), so this never
    reads a profile or vacancy and never writes a match or a notification. It still
    exists, returning a harmless 'disabled' summary, because cron-job.org (or any other
    scheduler) may still call it by name and must not get an error back."""
    return dict(DISABLED_MATCHING)


def run_daily_agent(db: Session, job_run_id: str | None = None) -> dict:
    """The matching Daily Agent is retired (it refreshed matches, then drafted a CV, a
    cover letter and an application for the strongest ones). Nothing is matched, drafted
    or notified any more. The job name stays valid because it carries the once-a-day
    optional admin sign-in digest and an external scheduler may still call it."""
    summary: dict = {**DISABLED_MATCHING, "detail": "The matching Daily Agent has been removed; "
                     "only the optional admin sign-in digest still runs here."}
    # The optional admin sign-in digest rides on this once-a-day job (no extra
    # workflow). Off for every admin unless they switched it on.
    try:
        summary["admin_login_digests"] = send_admin_login_digest(db)["sent"]
    except Exception:
        logger.warning("Admin sign-in digest step failed", exc_info=True)
    return summary


def send_admin_login_digest(db: Session) -> dict:
    """Email the optional digest of client sign-ins to admins who turned it on."""
    from app.services.admin_login_alerts import send_login_digest
    return send_login_digest(db, respect_interval=True)


def test_all_urls(db: Session, limit: int = 200, job_run_id: str | None = None,
                  max_seconds: float = 240.0, client: "httpx.Client | None" = None) -> dict:
    """Bulk careers-URL health check (blueprint sections 13 & 21).

    Fetches the careers URL of the active companies checked longest ago and
    updates each one's ``scraping_status`` / ``last_http_status`` /
    ``last_final_url`` / ``url_looks_like_careers`` exactly as the admin
    per-company ``/{id}/test-url`` endpoint does -- reusing ``test_url_sync``
    and ``status_from_result`` so a dead link found here is downgraded
    identically (200 + careers-looking -> ``ok``; a live page that doesn't look
    like careers -> ``needs_review``; a 404/timeout/DNS/SSL failure ->
    ``needs_real_url``; an empty URL -> ``no_url``).

    Time-bounded and rotating like :func:`scan_due_companies`: it stamps
    ``last_checked`` so successive runs advance through the database and each
    run returns inside a free scheduler's timeout instead of trying to fetch
    every URL in one request. ``limit`` is an upper cap for a lucky all-fast
    batch; ``max_seconds`` is the real throttle.

    Unlike the scan jobs this does NOT extract vacancies or email candidates --
    it only verifies that a stored link still resolves and looks right, so it is
    cheap enough to run across the whole database on a schedule and is the
    on-demand "verify every careers URL now and flag the dead ones" pass.
    """
    from app.services.url_tester import test_url_sync, status_from_result

    companies = (db.query(Company)
                 .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                         Company.careers_url.isnot(None))
                 # NULL last_checked (never checked) first, then oldest -- DB-portable.
                 .order_by(Company.last_checked.is_(None).desc(), Company.last_checked.asc())
                 .limit(limit)
                 .all())

    tested = ok = needs_review = dead = no_url = 0
    now = datetime.now(timezone.utc)
    started = time.monotonic()
    timed_out = False
    owns_client = client is None
    if owns_client:
        client = httpx.Client(
            timeout=settings.URL_TEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": settings.URL_TEST_USER_AGENT},
        )
    try:
        for company in companies:
            if time.monotonic() - started > max_seconds:
                timed_out = True
                break
            try:
                result = test_url_sync(company.careers_url, client=client)
            except Exception:
                logger.warning("test_all_urls: failed to test %s (%s)",
                               company.company_name, company.id, exc_info=True)
                continue
            company.last_checked = now
            company.last_http_status = result.status_code
            company.last_final_url = result.final_url
            company.url_looks_like_careers = result.looks_like_careers
            company.scraping_status = status_from_result(result)
            db.add(company)
            db.commit()
            tested += 1
            status_str = company.scraping_status
            if status_str == "ok":
                ok += 1
            elif status_str == "needs_review":
                needs_review += 1
            elif status_str == "no_url":
                no_url += 1
            else:
                dead += 1
    finally:
        if owns_client:
            client.close()

    return {"batch_limit": limit, "urls_tested": tested, "ok": ok,
            "needs_review": needs_review, "dead": dead, "no_url": no_url,
            "stopped_early_on_time_budget": timed_out}


def purge_expired_messages(db: Session, job_run_id: str | None = None) -> dict:
    """Storage limitation (POPIA s14): hard-delete expired temporary messages and stale abuse-report snapshots."""
    from app.api.routes_messages import purge_expired
    from app.api.routes_comments import purge_expired_comments
    return {"deleted_messages": purge_expired(db), "deleted_comments": purge_expired_comments(db)}


def send_daily_digest(db: Session) -> dict:
    """08:00 SAST (06:00 UTC): one "Your daily updates" email per opted-in user per day.

    Idempotent per user per SAST day, skips users with nothing new, honours the
    global send cap and DIGEST_DRY_RUN (see app/services/daily_digest.py).
    """
    from app.services.daily_digest import run_daily_digest
    return run_daily_digest(db)
