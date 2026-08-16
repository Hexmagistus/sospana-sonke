"""Lever postings strategy (public postings API)."""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text


class LeverStrategy(ScrapeStrategy):
    ats_type = "lever"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        token = (source.config or {}).get("token")
        if not token:
            raise ValueError("Lever source is missing a company token.")
        resp = client.get(f"https://api.lever.co/v0/postings/{token}?mode=json")
        resp.raise_for_status()
        out: list[RawVacancy] = []
        for p in resp.json():
            cats = p.get("categories") or {}
            out.append(RawVacancy(
                title=p.get("text", "").strip(),
                external_id=p.get("id"),
                location=cats.get("location"),
                department=cats.get("team") or cats.get("department"),
                employment_type=cats.get("commitment"),
                work_mode=(cats.get("workplaceType") or None),
                posting_date=None,
                description=html_to_text(p.get("descriptionPlain") or p.get("description")),
                application_url=p.get("hostedUrl") or p.get("applyUrl"),
                source_url=p.get("hostedUrl"),
                raw=p,
            ))
        return out
