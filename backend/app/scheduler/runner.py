"""Job runner: executes a named job and records a JobRun for observability."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.notification import JobRun
from app.scheduler.registry import JOBS


class UnknownJob(Exception):
    pass


def run_job(db: Session, name: str) -> JobRun:
    if name not in JOBS:
        raise UnknownJob(name)
    started = datetime.now(timezone.utc)
    run = JobRun(job_name=name, status="success", started_at=started)
    db.add(run)
    db.flush()
    try:
        summary = JOBS[name](db)
        run.detail = json.dumps(summary)[:2000]
        run.status = "success"
    except Exception as exc:  # record failure rather than crashing the scheduler
        run.status = "error"
        run.detail = f"{type(exc).__name__}: {exc}"[:2000]
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run
