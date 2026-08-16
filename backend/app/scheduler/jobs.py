"""Recurring job functions (blueprint section 22).

Each job is a plain function of a DB session so it can be invoked by any scheduler
(APScheduler / Celery beat / cron in production) or triggered manually by an admin.
Jobs are deterministic and safe to re-run.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.subscription import Subscription
from app.models.user import User
from app.services.scan_service import scan_company
from app.services.match_service import run_match_for_user
from app.services.subscription_service import get_or_create_subscription, has_active_access


def scan_all_companies(db: Session) -> dict:
    """Scan every active company that has a careers URL. Returns a summary."""
    companies = (db.query(Company)
                 .filter(Company.active.is_(True), Company.deleted_at.is_(None),
                         Company.careers_url.isnot(None))
                 .all())
    scanned = created = failed = 0
    for company in companies:
        try:
            reports = scan_company(db, company)
            scanned += 1
            created += sum(r.created for r in reports)
            failed += sum(1 for r in reports if r.status not in ("ok", "empty"))
        except Exception:
            failed += 1
    return {"companies_scanned": scanned, "vacancies_created": created, "sources_failed": failed}


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
