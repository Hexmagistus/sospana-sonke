"""Static-HTML strategy: parse schema.org JobPosting JSON-LD from a careers page.

Many careers pages embed structured `JobPosting` data in a
`<script type="application/ld+json">` block (a web standard search engines rely on).
Reading that is far more reliable than scraping arbitrary HTML. When no JSON-LD is
present, we return nothing and the source is flagged for review rather than guessing.
"""
from __future__ import annotations

import json
import re

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text

_LDJSON = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _iter_jobpostings(obj):
    """Yield JobPosting dicts from arbitrarily nested JSON-LD."""
    if isinstance(obj, list):
        for item in obj:
            yield from _iter_jobpostings(item)
    elif isinstance(obj, dict):
        t = obj.get("@type")
        types = t if isinstance(t, list) else [t]
        if "JobPosting" in types:
            yield obj
        if "@graph" in obj:
            yield from _iter_jobpostings(obj["@graph"])


def _location(job: dict) -> str | None:
    loc = job.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            return ", ".join(x for x in [addr.get("addressLocality"), addr.get("addressRegion"),
                                         addr.get("addressCountry")] if isinstance(x, str)) or None
    return None


class StaticHTMLStrategy(ScrapeStrategy):
    ats_type = "static"

    def parse_html(self, html: str, source_url: str | None = None) -> list[RawVacancy]:
        out: list[RawVacancy] = []
        for block in _LDJSON.findall(html):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            for job in _iter_jobpostings(data):
                title = job.get("title")
                if not title:
                    continue
                org = job.get("hiringOrganization")
                emp_type = job.get("employmentType")
                if isinstance(emp_type, list):
                    emp_type = ", ".join(emp_type)
                out.append(RawVacancy(
                    title=str(title).strip(),
                    external_id=str(job.get("identifier", {}).get("value"))
                        if isinstance(job.get("identifier"), dict) else None,
                    location=_location(job),
                    employment_type=emp_type,
                    posting_date=job.get("datePosted"),
                    closing_date=job.get("validThrough"),
                    description=html_to_text(job.get("description")),
                    application_url=(job.get("url") or source_url),
                    source_url=source_url,
                    raw=job,
                ))
        return out

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        resp = client.get(source.url)
        resp.raise_for_status()
        return self.parse_html(resp.text, source_url=str(resp.url))
