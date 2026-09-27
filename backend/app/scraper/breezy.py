"""Breezy HR public board (``https://{company}.breezy.hr/json``)."""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy
from app.scraper.politeness import request_with_backoff


def _location(value) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        name = value.get("name") or value.get("city")
        return str(name).strip() if name else None
    if isinstance(value, list) and value:
        return _location(value[0])
    return None


class BreezyStrategy(ScrapeStrategy):
    ats_type = "breezy"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        token = (source.config or {}).get("token")
        if not token:
            raise ValueError("Breezy source is missing a company subdomain.")
        resp = request_with_backoff(client, f"https://{token}.breezy.hr/json")
        resp.raise_for_status()
        payload = resp.json()
        jobs = payload if isinstance(payload, list) else []
        out: list[RawVacancy] = []
        for job in jobs:
            title = (job.get("name") or "").strip()
            if not title:
                continue
            link = job.get("url") or source.url
            out.append(RawVacancy(
                title=title,
                external_id=job.get("id"),
                location=_location(job.get("location") or job.get("locations")),
                department=job.get("department") if isinstance(job.get("department"), str) else None,
                employment_type=job.get("type") if isinstance(job.get("type"), str) else None,
                salary=job.get("salary") if isinstance(job.get("salary"), str) else None,
                posting_date=job.get("published_date"),
                application_url=link,
                source_url=link,
                raw={"id": job.get("id"), "name": title},
            ))
        return out
