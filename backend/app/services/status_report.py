"""Public status built from checks this process can actually run.

The scanner schedule is the 15-minute ``scan_due_companies`` cron. A scan is
stale after eight of those intervals with no finished scan log and no
successful job run. That is eight missed runs, not a separate uptime target.
Individual source failures use the existing alert threshold and are counted,
not hidden.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import JobRun
from app.models.scan_log import ScanLog
from app.models.vacancy import VacancySource

log = logging.getLogger(__name__)

# DEFAULT_SCHEDULE in app/scheduler/registry.py: "*/15 * * * *".
SCAN_INTERVAL_MINUTES = 15
# Eight missed runs of that cron.
STALE_AFTER_MINUTES = SCAN_INTERVAL_MINUTES * 8


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def database_check(db: Session) -> dict:
    """Run SELECT 1. The error text is not returned."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        log.exception("status database check failed")
        return {"status": "down"}
    return {"status": "ok"}


def scanner_check(db: Session, now: datetime | None = None) -> dict:
    """Newest finished scan, plus sources already at the failure threshold."""
    moment = now or datetime.now(timezone.utc)
    latest_log = _aware(db.query(func.max(ScanLog.finished_at)).scalar())
    latest_run = _aware(
        db.query(func.max(JobRun.finished_at))
        .filter(JobRun.job_name == "scan_due_companies", JobRun.status == "success")
        .scalar()
    )
    stamps = [item for item in (latest_log, latest_run) if item is not None]
    latest = max(stamps) if stamps else None
    age_minutes = None if latest is None else round((moment - latest).total_seconds() / 60, 1)
    if latest is None:
        state = "no_scans"
    elif age_minutes is not None and age_minutes > STALE_AFTER_MINUTES:
        state = "stale"
    else:
        state = "ok"
    failing = int(
        db.query(func.count(VacancySource.id))
        .filter(
            VacancySource.active.is_(True),
            VacancySource.consecutive_failures >= settings.SOURCE_FAILURE_ALERT_THRESHOLD,
        )
        .scalar()
        or 0
    )
    if state == "stale":
        log.error(
            "scanner stale: newest finish %s is past %s minutes",
            latest.isoformat() if latest else None,
            STALE_AFTER_MINUTES,
        )
    return {
        "status": state,
        "latest_finished_at": latest.isoformat() if latest else None,
        "age_minutes": age_minutes,
        "schedule_minutes": SCAN_INTERVAL_MINUTES,
        "stale_after_minutes": STALE_AFTER_MINUTES,
        "failure_threshold": settings.SOURCE_FAILURE_ALERT_THRESHOLD,
        "sources_at_failure_threshold": failing,
    }


def status_report(db: Session, now: datetime | None = None) -> dict:
    database = database_check(db)
    scanner = scanner_check(db, now=now)
    if database["status"] != "ok":
        overall = "down"
    elif scanner["status"] != "ok" or scanner["sources_at_failure_threshold"] > 0:
        overall = "degraded"
    else:
        overall = "ok"
    return {
        "status": overall,
        "checked_at": (now or datetime.now(timezone.utc)).isoformat(),
        "components": {
            "api": {"status": "ok"},
            "database": database,
            "scanner": scanner,
        },
    }
