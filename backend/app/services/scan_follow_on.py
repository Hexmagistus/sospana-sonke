"""Keep scanning for a few minutes after the scan cron's request has answered.

GitHub runs the */15 scan workflow only every 4 to 8 hours in practice. One
~20 second batch per run reached about 100 of 5,000 careers pages a day, so
South African sources went weeks without a check and their open posts fell
out of the "seen recently" window and off the site.

After ``scan_due_companies`` answers the cron, this starts one background
thread that keeps scanning due sources in larger batches for up to
``SCAN_FOLLOW_ON_SECONDS`` (default 480 s, under Render's 15-minute idle
spin-down) and stops early when nothing is due. The queue order is the usual
one (scan_runner.select_due): South Africa first, then the rest of SADC, the
rest of Africa, then other regions. Sources are claimed compare-and-set before
each fetch, so this thread and a later cron call never scan the same source.
Only one follow-on runs per process at a time. Set SCAN_FOLLOW_ON_SECONDS=0 to
switch it off. It never runs under ENV=test.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger(__name__)

DEFAULT_FOLLOW_ON_SECONDS = 480.0
BATCH_LIMIT = 60
BATCH_SECONDS = 40.0
JOB_NAME = "scan_follow_on"

_running = threading.Lock()


def follow_on_seconds() -> float:
    from app.core.config import settings
    if settings.ENV == "test":
        return 0.0
    try:
        return max(0.0, float(os.getenv("SCAN_FOLLOW_ON_SECONDS", DEFAULT_FOLLOW_ON_SECONDS)))
    except ValueError:
        return DEFAULT_FOLLOW_ON_SECONDS


def run_follow_on(batch: Callable[[], dict], seconds: float,
                  clock: Callable[[], float] = time.monotonic) -> dict:
    """Call ``batch`` until ``seconds`` have passed or nothing is due.

    A batch is not started unless BATCH_SECONDS remain, so the loop ends on
    time. Returns totals for the JobRun log.
    """
    started = clock()
    totals = {"batches": 0, "companies_scanned": 0, "vacancies_created": 0,
              "sources_failed": 0, "errors": 0, "stopped": "time"}
    while clock() - started + BATCH_SECONDS <= seconds:
        try:
            summary = batch() or {}
        except Exception:
            logger.warning("scan follow-on: batch failed", exc_info=True)
            totals["errors"] += 1
            if totals["errors"] >= 3:
                totals["stopped"] = "errors"
                break
            continue
        totals["batches"] += 1
        for key in ("companies_scanned", "vacancies_created", "sources_failed"):
            totals[key] += int(summary.get(key) or 0)
        if not summary.get("due_selected"):
            totals["stopped"] = "nothing_due"
            break
    totals["elapsed_seconds"] = round(clock() - started, 1)
    return totals


def _thread_main(seconds: float) -> None:
    from app.db.session import SessionLocal
    from app.models.notification import JobRun
    from app.services.scan_batch import DEFAULT_WORKERS, run_scan_batch

    def batch() -> dict:
        db = SessionLocal()
        try:
            return run_scan_batch(db, limit=BATCH_LIMIT, max_seconds=BATCH_SECONDS,
                                  workers=DEFAULT_WORKERS)
        finally:
            db.close()

    started = datetime.now(timezone.utc)
    try:
        totals = run_follow_on(batch, seconds)
        db = SessionLocal()
        try:
            db.add(JobRun(job_name=JOB_NAME, status="success", started_at=started,
                          finished_at=datetime.now(timezone.utc), detail=json.dumps(totals)[:2000]))
            db.commit()
        finally:
            db.close()
        logger.info("scan follow-on finished: %s", totals)
    except Exception:
        logger.exception("scan follow-on crashed")
    finally:
        _running.release()


def start_follow_on() -> bool:
    """Start the background follow-on unless one is running or it is switched off."""
    seconds = follow_on_seconds()
    if seconds < BATCH_SECONDS:
        return False
    if not _running.acquire(blocking=False):
        return False
    try:
        threading.Thread(target=_thread_main, args=(seconds,), name="scan-follow-on",
                         daemon=True).start()
    except Exception:
        _running.release()
        logger.warning("scan follow-on: could not start", exc_info=True)
        return False
    return True
