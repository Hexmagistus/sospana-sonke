"""Workday candidate-site strategy.

The public career site loads listings from
``POST https://{host}/wday/cxs/{tenant}/{site}/jobs``. That is the same JSON
the candidate's browser requests. No headless browser, and nothing that tries
to defeat a block — if Workday refuses the request, the source is recorded
as a failure and the rest of the scan continues.
"""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy
from app.scraper.politeness import request_with_backoff

_PAGE = 20
_CAP = 60


class WorkdayStrategy(ScrapeStrategy):
    ats_type = "workday"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        cfg = source.config or {}
        tenant, site, host = cfg.get("tenant"), cfg.get("site"), cfg.get("host")
        if not (tenant and site and host):
            raise ValueError("Workday source is missing tenant, site, or host.")
        endpoint = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        out: list[RawVacancy] = []
        offset = 0
        total = None
        while offset < _CAP:
            resp = request_with_backoff(client, endpoint, method="POST", json_body={
                "appliedFacets": cfg.get("facets") or {},
                "limit": _PAGE, "offset": offset, "searchText": "",
            })
            resp.raise_for_status()
            payload = resp.json()
            if total is None:
                total = int(payload.get("total") or 0)
            postings = payload.get("jobPostings") or []
            if not postings:
                break
            for job in postings:
                title = (job.get("title") or "").strip()
                if not title:
                    continue
                path = job.get("externalPath") or ""
                link = f"https://{host}/{site}{path}" if path else source.url
                out.append(RawVacancy(
                    title=title,
                    external_id=path or None,
                    location=job.get("locationsText") or None,
                    posting_date=job.get("postedOn"),
                    application_url=link,
                    source_url=link,
                    raw={"title": title, "externalPath": path},
                ))
            offset += len(postings)
            if total is not None and offset >= total:
                break
        return out
