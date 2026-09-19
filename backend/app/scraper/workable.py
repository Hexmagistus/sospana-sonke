"""Workable careers-site strategy (public, no-key widget JSON endpoint).

``https://www.workable.com/api/accounts/{account}?details=true`` is the same
public feed a Workable-hosted careers page's own widget calls to render its
listings (redirects to an equivalent ``apply.workable.com`` URL); no
authentication is required.
"""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text
from app.scraper.politeness import request_with_backoff


class WorkableStrategy(ScrapeStrategy):
    ats_type = "workable"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        account = (source.config or {}).get("token")
        if not account:
            raise ValueError("Workable source is missing a company account name.")
        url = f"https://www.workable.com/api/accounts/{account}?details=true"
        resp = request_with_backoff(client, url)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
        out: list[RawVacancy] = []
        for j in jobs:
            loc = j.get("location") or {}
            location = loc.get("location_str") or ", ".join(
                x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x) or None
            application_url = j.get("url") or j.get("shortlink")
            out.append(RawVacancy(
                title=(j.get("title") or "").strip(),
                external_id=j.get("shortcode") or (str(j.get("id")) if j.get("id") is not None else None),
                location=location,
                work_mode=("remote" if loc.get("telecommuting") else None),
                department=j.get("department"),
                employment_type=j.get("employment_type"),
                posting_date=j.get("published_on") or j.get("created_at"),
                description=html_to_text(j.get("full_description") or j.get("description")),
                application_url=application_url,
                source_url=j.get("shortlink") or application_url,
                raw=j,
            ))
        return out
