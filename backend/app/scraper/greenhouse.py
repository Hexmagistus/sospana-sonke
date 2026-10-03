"""Greenhouse job-board strategy (public boards API).

The list feed (``/jobs`` without ``content=true``) is the vacancy index. The
same URL with ``content=true`` repeats every description in one body, and a
large board (Anthropic's is about 9 MB for 641 roles) exceeds
``MAX_RESPONSE_BYTES``. Asking for that body first makes the scan fail with
``RESPONSE_TOO_LARGE`` and stores nothing, so the open-vacancy count stays at
zero.

Fetch the list first. When the board is small enough, one follow-up with
``content=true`` fills descriptions. If that follow-up is over the size cap,
or the board is larger than ``GREENHOUSE_DETAIL_LIMIT``, keep the list. The
cap, SSRF check, and backoff stay on every request.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text
from app.scraper.politeness import request_with_backoff

logger = logging.getLogger(__name__)

# One content=true body for a short board stays well under the 5 MB cap.
# A longer board is counted from the list alone; per-job detail would be a
# separate request per role and would blow the scan time budget.
GREENHOUSE_DETAIL_LIMIT = 40

_API = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseStrategy(ScrapeStrategy):
    ats_type = "greenhouse"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        token = (source.config or {}).get("token")
        if not token:
            raise ValueError("Greenhouse source is missing a board token.")
        listed = _job_list(request_with_backoff(client, _jobs_url(token, content=False)))
        if listed and _missing_content(listed) and len(listed) <= GREENHOUSE_DETAIL_LIMIT:
            listed = _with_content(client, token, listed)
        return [_to_raw(job) for job in listed]


def _jobs_url(token: str, *, content: bool) -> str:
    url = f"{_API}/{quote(str(token), safe='')}/jobs"
    return f"{url}?content=true" if content else url


def _job_list(resp: httpx.Response) -> list[dict]:
    resp.raise_for_status()
    jobs = resp.json().get("jobs") or []
    if not isinstance(jobs, list):
        return []
    return [job for job in jobs if isinstance(job, dict)]


def _missing_content(jobs: list[dict]) -> bool:
    return any(not str(job.get("content") or "").strip() for job in jobs)


def _with_content(client: httpx.Client, token: str, listed: list[dict]) -> list[dict]:
    """One rich fetch. A size-cap or HTTP failure keeps the list we already have."""
    try:
        rich = _job_list(request_with_backoff(client, _jobs_url(token, content=True)))
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Greenhouse board %s: description feed unavailable (%s); keeping %s listed jobs",
            token, type(exc).__name__, len(listed),
        )
        return listed
    if not rich:
        return listed
    return _merge_jobs(listed, rich)


def _merge_jobs(listed: list[dict], rich: list[dict]) -> list[dict]:
    """Prefer a rich job when the id matches. Never drop a list-only id."""
    rich_by_id = {
        str(job["id"]): job
        for job in rich
        if job.get("id") is not None
    }
    merged: list[dict] = []
    seen: set[str] = set()
    for job in listed:
        job_id = str(job["id"]) if job.get("id") is not None else None
        if job_id and job_id in rich_by_id:
            merged.append(rich_by_id[job_id])
            seen.add(job_id)
        else:
            merged.append(job)
            if job_id:
                seen.add(job_id)
    for job in rich:
        job_id = str(job["id"]) if job.get("id") is not None else None
        if job_id and job_id not in seen:
            merged.append(job)
            seen.add(job_id)
    return merged


def _to_raw(job: dict) -> RawVacancy:
    location = (job.get("location") or {}).get("name")
    departments = job.get("departments") or []
    names = [
        dept.get("name", "")
        for dept in departments
        if isinstance(dept, dict) and dept.get("name")
    ]
    return RawVacancy(
        title=(job.get("title") or "").strip(),
        external_id=str(job["id"]) if job.get("id") is not None else None,
        location=location,
        department=", ".join(names) or None,
        posting_date=job.get("updated_at") or job.get("first_published"),
        description=html_to_text(job.get("content")),
        application_url=job.get("absolute_url"),
        source_url=job.get("absolute_url"),
        raw=job,
    )
