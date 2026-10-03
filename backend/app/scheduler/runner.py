"""Job runner: executes a named job and records a JobRun for observability."""
from __future__ import annotations

import inspect
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.notification import JobRun
from app.scheduler.registry import JOBS

logger = logging.getLogger(__name__)


class UnknownJob(Exception):
    pass


def run_job(db: Session, name: str) -> JobRun:
    if name not in JOBS:
        raise UnknownJob(name)
    started = datetime.now(timezone.utc)
    run = JobRun(job_name=name, status="success", started_at=started)
    db.add(run)
    db.flush()
    run_id = run.id
    try:
        fn = JOBS[name]
        # Jobs that support alerting on what they find (e.g. new-job broadcasts)
        # accept a job_run_id kwarg for idempotency; others just take (db).
        kwargs = {"job_run_id": run.id} if "job_run_id" in inspect.signature(fn).parameters else {}
        summary = fn(db, **kwargs)
        run.detail = json.dumps(summary)[:2000]
        run.status = "success"
    except Exception as exc:  # record failure rather than crashing the scheduler
        # The job may have left the transaction aborted (a too-long INSERT does).
        # Writing the error row before rollback raises again, and the cron
        # route then returns a bare 500 instead of this JobRun.
        logger.exception("Scheduled job %r failed", name)
        message = f"{type(exc).__name__}: {exc}"[:2000]
        db.rollback()
        run = db.get(JobRun, run_id)
        if run is None:
            run = JobRun(id=run_id, job_name=name, status="error", started_at=started)
            db.add(run)
        run.status = "error"
        run.detail = message
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run
