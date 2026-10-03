"""Scheduler registry: named jobs and their admin-configurable cron schedule.

The default cron strings mirror the blueprint's example cadence. They are stored
in system_settings under 'schedule_config' so an administrator can change the
intervals without a code change; the deployed scheduler reads them at load.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.match import SystemSetting
from app.scheduler.jobs import (
    scan_all_companies, scan_south_africa, scan_due_companies, match_all_candidates, check_link_changes,
    test_all_urls, close_expired_vacancies, run_daily_agent, purge_expired_messages,
    send_admin_login_digest,
    discover_company_icons,
)

# name -> callable(db) -> summary dict
JOBS = {
    "scan_all_companies": scan_all_companies,   # full sweep, every country (slow; manual/admin use)
    "scan_south_africa": scan_south_africa,     # full sweep, South Africa only (current rollout phase)
    "scan_due_companies": scan_due_companies,   # fast rotating batch (external cron)
    "close_expired_vacancies": close_expired_vacancies,  # DB-only sweep: is_open=False past closing_date
    "discover_company_icons": discover_company_icons,  # polite fetch-once icon store (robots.txt, rate-limited, small batch)
    "match_all_candidates": match_all_candidates,
    "check_link_changes": check_link_changes,   # fast rotating batch: page-hash "did it change" check
    "test_all_urls": test_all_urls,             # rotating, time-bounded careers-URL health check + status downgrade
    "purge_expired_messages": purge_expired_messages,  # hourly: delete expired temporary messages (POPIA storage limitation)
    "run_daily_agent": run_daily_agent,         # proactive daily agent: match -> draft CV/cover letter -> queue
    "send_admin_login_digest": send_admin_login_digest,  # optional (per-admin, off by default) client sign-in digest
}

DEFAULT_SCHEDULE = {
    "scan_due_companies": "*/15 * * * *",        # every 15 min via GitHub Actions (best-effort)
    "scan_all_companies": "0 */6 * * *",         # every 6 hours
    "close_expired_vacancies": "0 1 * * *",      # nightly at 01:00, before matching — keeps is_open accurate
    "discover_company_icons": "*/30 * * * *",      # ~12 companies per run, spaced out; never on a page view
    "match_all_candidates": "0 2 * * *",         # nightly at 02:00
    "check_link_changes": "0 */4 * * *",         # every 4 hours — rotates through the list
    "test_all_urls": "0 4 * * *",                # daily 04:00 — rotating careers-URL health check
    "purge_expired_messages": "15 * * * *",      # hourly at :15
    "run_daily_agent": "0 3 * * *",              # nightly at 03:00 — after expiry cleanup, before URL health check
    "send_admin_login_digest": "30 5 * * *",     # daily 05:30; also runs at the end of run_daily_agent
}

SCHEDULE_KEY = "schedule_config"


def get_schedule(db: Session) -> dict:
    row = db.query(SystemSetting).filter(SystemSetting.key == SCHEDULE_KEY).first()
    return {**DEFAULT_SCHEDULE, **(row.value if row else {})}


def set_schedule(db: Session, schedule: dict) -> dict:
    # Only accept keys for jobs we actually have.
    cleaned = {k: v for k, v in schedule.items() if k in JOBS}
    row = db.query(SystemSetting).filter(SystemSetting.key == SCHEDULE_KEY).first()
    merged = {**DEFAULT_SCHEDULE, **cleaned}
    if row is None:
        row = SystemSetting(key=SCHEDULE_KEY, value=merged, description="Scheduler cron intervals.")
        db.add(row)
    else:
        row.value = merged
        row.version += 1
    db.commit()
    return merged
