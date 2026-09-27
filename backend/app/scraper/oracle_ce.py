"""Oracle Recruiting Cloud candidate-experience strategy.

``recruitingCEJobRequisitions`` is the public JSON the career site uses to
fill its job list. ``siteNumber=CX`` is the default board on a host that
belongs to one employer; ``CX_1`` and similar come from the URL path.
"""
from __future__ import annotations

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy
from app.scraper.politeness import request_with_backoff

_PAGE = 25
_CAP = 75


class OracleCEStrategy(ScrapeStrategy):
    ats_type = "oracle"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        cfg = source.config or {}
        host = cfg.get("host")
        site_number = cfg.get("site_number") or "CX"
        site_name = cfg.get("site_name") or site_number
        if not host:
            raise ValueError("Oracle source is missing a host.")
        out: list[RawVacancy] = []
        offset = 0
        total = None
        while offset < _CAP:
            url = (
                f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                f"?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site_number}"
                f",limit={_PAGE},offset={offset},sortBy=POSTING_DATES_DESC"
            )
            resp = request_with_backoff(client, url)
            resp.raise_for_status()
            items = resp.json().get("items") or []
            item = items[0] if items else {}
            if total is None:
                total = int(item.get("TotalJobsCount") or 0)
            reqs = item.get("requisitionList") or []
            if not reqs:
                break
            for req in reqs:
                title = (req.get("Title") or "").strip()
                if not title:
                    continue
                job_id = req.get("Id")
                link = source.url
                if job_id:
                    link = (
                        f"https://{host}/hcmUI/CandidateExperience/en/sites/"
                        f"{site_name}/job/{job_id}"
                    )
                location = ", ".join(
                    x for x in [req.get("PrimaryLocation"), req.get("PrimaryLocationCountry")]
                    if isinstance(x, str) and x
                ) or None
                out.append(RawVacancy(
                    title=title,
                    external_id=str(job_id) if job_id else None,
                    location=location,
                    employment_type=req.get("JobType") or req.get("ContractType"),
                    posting_date=req.get("PostedDate"),
                    closing_date=req.get("PostingEndDate"),
                    application_url=link,
                    source_url=link,
                    raw={"Id": job_id, "Title": title},
                ))
            offset += len(reqs)
            if total is not None and offset >= total:
                break
        return out
