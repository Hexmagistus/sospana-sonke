"""Recurring job functions (blueprint section 22).

Each job is a plain function of a DB session so it can be invoked by any scheduler
(APScheduler / Celery beat / cron in production) or triggered manually by an admin.
Jobs are deterministic and safe to re-run.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.subscription import Subscription
from app.models.user import User
from app.services.scan_service import scan_company
from app.services.match_service import run_match_for_user
from app.services.subscription_service import get_or_create_subscription, has_active_access


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


def scan_due_companies(db: Session, limit: int = 25, job_run_id: str | None = None) -> dict:
    """Scan the N companies checked longest ago (never-checked first), then stamp
    them so the next run picks up the following batch.

    Keeps each run fast (seconds, not minutes) so a free external scheduler can
    call it reliably every few hours; the whole database still cycles over a day.
    """
    companies = (db.query(Company)
                 .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                         Company.careers_url.isnot(None))
                 # NULL last_checked (never scanned) first, then oldest — DB-portable.
                 .order_by(Company.last_checked.is_(None).desc(), Company.last_checked.asc())
                 .limit(limit)
                 .all())
    scanned = created = failed = 0
    new_vacancy_ids: list[str] = []
    now = datetime.now(timezone.utc)
    for company in companies:
        try:
            reports = scan_company(db, company)
            scanned += 1
            created += sum(r.created for r in reports)
            failed += sum(1 for r in reports if r.status not in ("ok", "empty"))
            for r in reports:
                new_vacancy_ids.extend(r.created_vacancy_ids)
        except Exception:
            failed += 1
        company.last_checked = now
        db.add(company)
        db.commit()
    candidates_alerted = _alert_candidates_of_new_jobs(db, new_vacancy_ids, job_run_id)
    return {"batch_limit": limit, "companies_scanned": scanned,
            "vacancies_created": created, "sources_failed": failed,
            "candidates_alerted": candidates_alerted}


def match_all_candidates(db: Session) -> dict:
    """Run matching for every candidate with active access; notifications fire inside."""
    users = db.query(User).filter(User.role == "candidate", User.is_active.is_(True)).all()
    ran = matched = 0
    for user in users:
        if not has_active_access(get_or_create_subscription(db, user.id)):
            continue
        summary = run_match_for_user(db, user.id)
        ran += 1
        matched += summary.matched
    return {"candidates_matched": ran, "total_matches": matched}
