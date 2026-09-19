"""Recruitee careers-site strategy (public, no-key JSON endpoint).

Every Recruitee-hosted careers site exposes its own live listings at
``https://{subdomain}.recruitee.com/api/offers/`` with no authentication --
the same page a candidate's browser would call to render the jobs list, so
using it is not a bypass of anything, just reading the public feed directly
instead of scraping the rendered HTML.
"""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text
from app.scraper.politeness import request_with_backoff


class RecruiteeStrategy(ScrapeStrategy):
    ats_type = "recruitee"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        subdomain = (source.config or {}).get("token")
        if not subdomain:
            raise ValueError("Recruitee source is missing a company subdomain.")
        url = f"https://{subdomain}.recruitee.com/api/offers/"
        resp = request_with_backoff(client, url)
        resp.raise_for_status()
        offers = resp.json().get("offers", [])
        out: list[RawVacancy] = []
        for o in offers:
            location = o.get("location") or o.get("city")
            work_mode = "remote" if o.get("remote") else ("hybrid" if o.get("hybrid") else None)
            careers_url = o.get("careers_url")
            out.append(RawVacancy(
                title=(o.get("title") or "").strip(),
                external_id=str(o.get("id")) if o.get("id") is not None else o.get("slug"),
                location=location,
                department=o.get("department"),
                work_mode=work_mode,
                employment_type=o.get("employment_type_code"),
                posting_date=o.get("published_at"),
                closing_date=o.get("close_at"),
                description=html_to_text(o.get("description")),
                application_url=careers_url,
                source_url=careers_url,
                raw=o,
            ))
        return out
