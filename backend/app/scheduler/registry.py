"""Scheduler registry: named jobs and their admin-configurable cron schedule.

The default cron strings mirror the blueprint's example cadence. They are stored
in system_settings under 'schedule_config' so an administrator can change the
intervals without a code change; the deployed scheduler reads them at load.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.match import SystemSetting
from app.scheduler.jobs import scan_all_companies, match_all_candidates

# name -> callable(db) -> summary dict
JOBS = {
    "scan_all_companies": scan_all_companies,
    "match_all_candidates": match_all_candidates,
}

DEFAULT_SCHEDULE = {
    "scan_all_companies": "0 */6 * * *",     # every 6 hours
    "match_all_candidates": "0 2 * * *",     # nightly at 02:00
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
