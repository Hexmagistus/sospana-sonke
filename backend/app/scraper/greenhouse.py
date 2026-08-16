"""Greenhouse job-board strategy (public boards API)."""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text


class GreenhouseStrategy(ScrapeStrategy):
    ats_type = "greenhouse"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        token = (source.config or {}).get("token")
        if not token:
            raise ValueError("Greenhouse source is missing a board token.")
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        resp = client.get(url)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
        out: list[RawVacancy] = []
        for j in jobs:
            loc = (j.get("location") or {}).get("name")
            out.append(RawVacancy(
                title=j.get("title", "").strip(),
                external_id=str(j.get("id")) if j.get("id") is not None else None,
                location=loc,
                department=", ".join(d.get("name", "") for d in j.get("departments", []) if d) or None,
                posting_date=j.get("updated_at") or j.get("first_published"),
                description=html_to_text(j.get("content")),
                application_url=j.get("absolute_url"),
                source_url=j.get("absolute_url"),
                raw=j,
            ))
        return out
