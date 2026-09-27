"""Pinpoint public postings feed (``https://{company}.pinpointhq.com/postings.json``)."""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text
from app.scraper.politeness import request_with_backoff


class PinpointStrategy(ScrapeStrategy):
    ats_type = "pinpoint"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        host = (source.config or {}).get("host")
        if not host:
            raise ValueError("Pinpoint source is missing a host.")
        resp = request_with_backoff(client, f"https://{host}/postings.json")
        resp.raise_for_status()
        jobs = resp.json().get("data") or []
        out: list[RawVacancy] = []
        for job in jobs:
            title = (job.get("title") or "").strip()
            if not title:
                continue
            link = job.get("url") or source.url
            description = html_to_text(job.get("description"))
            if len(description) > 4000:
                description = description[:4000]
            out.append(RawVacancy(
                title=title,
                external_id=str(job.get("id")) if job.get("id") is not None else None,
                employment_type=job.get("employment_type_text") or job.get("employment_type"),
                posting_date=job.get("published_at") or job.get("created_at"),
                closing_date=job.get("deadline_at"),
                description=description or None,
                application_url=link,
                source_url=link,
                raw={"id": job.get("id"), "title": title},
            ))
        return out
