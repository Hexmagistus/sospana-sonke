"""SmartRecruiters postings strategy (public postings API)."""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text


class SmartRecruitersStrategy(ScrapeStrategy):
    ats_type = "smartrecruiters"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        token = (source.config or {}).get("token")
        if not token:
            raise ValueError("SmartRecruiters source is missing a company identifier.")
        resp = client.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100")
        resp.raise_for_status()
        out: list[RawVacancy] = []
        for p in resp.json().get("content", []):
            loc = p.get("location") or {}
            location = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x) or None
            out.append(RawVacancy(
                title=(p.get("name") or "").strip(),
                external_id=p.get("id") or p.get("uuid"),
                location=location,
                work_mode=("remote" if loc.get("remote") else None),
                department=(p.get("department") or {}).get("label"),
                posting_date=p.get("releasedDate"),
                description=html_to_text((p.get("jobAd") or {}).get("sections", {}).get("jobDescription", {}).get("text")),
                application_url=p.get("applyUrl") or p.get("ref"),
                source_url=p.get("ref"),
                raw=p,
            ))
        return out
