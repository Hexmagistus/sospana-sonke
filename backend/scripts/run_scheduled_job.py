"""Run a scheduled job by name (for cron / APScheduler / Celery beat to call).

Usage:
    python -m scripts.run_scheduled_job match_all_candidates
    python -m scripts.run_scheduled_job scan_all_companies

In production, point your scheduler at these commands using the cron intervals
from GET /api/v1/admin/schedule (an admin can change them without a code change).
"""
import sys

from app.db.session import SessionLocal, init_db
from app.scheduler.registry import JOBS
from app.scheduler.runner import run_job, UnknownJob


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: python -m scripts.run_scheduled_job <job>\nKnown jobs: {', '.join(JOBS)}")
        raise SystemExit(2)
    init_db()
    db = SessionLocal()
    try:
        run = run_job(db, sys.argv[1])
        print(f"Job '{run.job_name}' finished with status={run.status}: {run.detail}")
    except UnknownJob:
        print(f"Unknown job '{sys.argv[1]}'. Known jobs: {', '.join(JOBS)}")
        raise SystemExit(2)
    finally:
        db.close()


if __name__ == "__main__":
    main()
