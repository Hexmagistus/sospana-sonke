"""Last good public jobs list, served when the database cannot answer.

Every successful unfiltered first-page query writes the list to a JSON file.
When the database errors, the routes read that file, or the bootstrap file
baked into the deploy, and drop anything whose closing date has passed.
Expired roles are never returned from a snapshot.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from app.services.opportunity_expiry import sa_today

log = logging.getLogger(__name__)

BAKED = Path(__file__).resolve().parent.parent / "data" / "jobs_snapshot.json"
RUNTIME = Path(os.environ.get("JOBS_SNAPSHOT_PATH", str(Path(tempfile.gettempdir()) / "ss_jobs_snapshot.json")))


def save(jobs: list[dict], path: Path | None = None) -> None:
    """Persist the list. Never raises: a failed write must not break the request."""
    target = path or RUNTIME
    try:
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "saved_at": datetime.now(timezone.utc).isoformat(), "jobs": jobs,
        }, default=str), encoding="utf-8")
        tmp.replace(target)
    except Exception:  # pragma: no cover - disk full, read-only FS
        log.warning("jobs snapshot write failed", exc_info=True)


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        return None
    return data


def _closing(job: dict) -> date | None:
    value = job.get("closing_date")
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def unexpired(jobs: list[dict], today: date | None = None) -> list[dict]:
    """Open roles only: a closing date before today removes the row."""
    day = today or sa_today()
    out = []
    for job in jobs:
        if job.get("is_open") is False:
            continue
        closes = _closing(job)
        if closes is not None and closes < day:
            continue
        out.append(job)
    return out


def load(today: date | None = None, runtime: Path | None = None, baked: Path | None = None) -> tuple[list[dict], str | None]:
    """(open jobs, saved_at). The runtime file wins over the baked one when it has open rows."""
    for path in (runtime or RUNTIME, baked or BAKED):
        data = _read(path)
        if data is None:
            continue
        jobs = unexpired(data["jobs"], today)
        if jobs:
            return jobs, data.get("saved_at")
    return [], None


def matches(job: dict, q: str | None, country: str | None, employer: str | None,
            opportunity_type: str | None) -> bool:
    if q and q.strip() and q.strip().lower() not in str(job.get("title", "")).lower():
        return False
    if country and country.strip():
        name = country.strip()
        if name not in (job.get("company_country"), job.get("country")):
            return False
    if employer and employer.strip() and employer.strip().lower() not in str(job.get("company_name", "")).lower():
        return False
    if opportunity_type and opportunity_type.strip() and job.get("opportunity_type") != opportunity_type.strip():
        return False
    return True
