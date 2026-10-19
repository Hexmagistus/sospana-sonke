"""SmartRecruiters postings strategy (public postings API)."""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text
from app.scraper.politeness import request_with_backoff


def _posting_page(token: str, posting: dict) -> str | None:
    """The employer's public advert page. ``ref`` is the JSON API, not a page."""
    posting_id = posting.get("id")
    if posting_id:
        return f"https://jobs.smartrecruiters.com/{token}/{posting_id}"
    ref = posting.get("ref") or ""
    return None if "api.smartrecruiters.com" in ref else (ref or None)


class SmartRecruitersStrategy(ScrapeStrategy):
    ats_type = "smartrecruiters"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        token = (source.config or {}).get("token")
        if not token:
            raise ValueError("SmartRecruiters source is missing a company identifier.")
        out: list[RawVacancy] = []
        offset = 0
        while offset < 200:
            country = (source.config or {}).get("country")
            country_q = f"&country={country}" if country else ""
            resp = request_with_backoff(
                client,
                f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100&offset={offset}{country_q}",
            )
            resp.raise_for_status()
            payload = resp.json()
            page = payload.get("content") or []
            if not page:
                break
            for p in page:
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
                    application_url=p.get("applyUrl") or _posting_page(token, p),
                    source_url=_posting_page(token, p),
                    raw={"id": p.get("id"), "name": p.get("name")},
                ))
            offset += len(page)
            total = payload.get("totalFound")
            if total is not None and offset >= int(total):
                break
        return out
