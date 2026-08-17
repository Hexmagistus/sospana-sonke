"""Static-HTML strategy: read vacancies from a server-rendered careers page.

Two passes, in order of reliability:
1. schema.org JobPosting JSON-LD (a web standard) — most reliable when present.
2. A heuristic link extractor for plain-HTML job lists (e.g. SANParks, SITA,
   SANRAL): anchors that point at a job detail/PDF and whose text reads like a
   role title. JavaScript-rendered portals return nothing here (correctly) and
   are left for the browser strategy / direct link.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy, html_to_text

_LDJSON = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

# ---- heuristic link extractor ----------------------------------------------
_ROLE_KW = ("manager", "officer", "engineer", "administrator", "clerk", "specialist",
    "coordinator", "technician", "developer", "analyst", "controller", "team leader",
    "leader", "executive", "operator", "dealer", "intern", "graduate", "bursary",
    "ranger", "buyer", "accountant", "auditor", "adviser", "advisor", "consultant",
    "supervisor", "cleaner", "driver", "receptionist", "secretary", "nurse",
    "practitioner", "lecturer", "researcher", "economist", "attorney", "technologist",
    "artisan", "fitter", "electrician", "boilermaker", "learnership", "apprentice",
    "cashier", "teller", "planner", "scientist", "pilot", "internship")
_STRONG_HREF = re.compile(r'/(detail|vacanc|requisition|position|job|opportunit|posting|req)(/|-|\?|$)', re.I)
_BLACKLIST = ("manual", "policy", "plan", "committee", "board of", "privacy", "notice",
    "communication", "bank details", "download", "sign in", "register", "procurement",
    "standards &", "how to apply", "terms", "cookie", "contact us", "about us", "login",
    "e-procurement", "paia")
_STOP = {"open vacancies", "closed vacancies", "apply", "apply now", "apply online",
    "view more", "read more", "more", "home", "careers", "vacancies"}
_A = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_ADVERT = re.compile(r'^\s*(re[\s\-]*advert(isement)?\s*[-:]?\s*)+', re.I)


def _clean_text(t: str) -> str:
    t = re.sub(r'<[^>]+>', ' ', t)
    t = (t.replace('&amp;', '&').replace('&#39;', "'").replace('&nbsp;', ' ')
         .replace('&quot;', '"').replace('&#8211;', '-'))
    return re.sub(r'\s+', ' ', t).strip()


def _clean_title(t: str) -> str:
    if t.lower().endswith('.pdf'):
        t = t[:-4]
    t = _ADVERT.sub('', t)                    # drop "Re-Advert -" prefixes
    t = t.replace('_', ' ')
    return re.sub(r'\s+', ' ', t).strip()


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


def _iter_jobpostings(obj):
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


class StaticHTMLStrategy(ScrapeStrategy):
    ats_type = "static"

    def parse_jsonld(self, html: str, source_url: str | None = None) -> list[RawVacancy]:
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

    def parse_links(self, html: str, source_url: str | None = None) -> list[RawVacancy]:
        base = source_url or ""
        out: list[RawVacancy] = []
        seen: set[str] = set()
        for href, inner in _A.findall(html):
            t = _clean_text(inner)
            low = t.lower()
            hrefl = href.lower()
            if not t or len(t) < 6 or len(t) > 100:
                continue
            if low in _STOP or any(b in low for b in _BLACKLIST):
                continue
            if '/list/' in hrefl or '/browse' in hrefl:
                continue
            role = any(k in low for k in _ROLE_KW)
            pdf_job = hrefl.endswith('.pdf') and role
            detailish = any(k in hrefl for k in ('detail', '.pdf', '/job', 'vacanc', 'requisition'))
            strong = bool(_STRONG_HREF.search(hrefl))
            keep = pdf_job or (strong and role) or (role and len(t.split()) >= 2 and detailish)
            if not keep:
                continue
            if low in seen:
                continue
            seen.add(low)
            title = _clean_title(t)
            if not title:
                continue
            out.append(RawVacancy(
                title=title,
                application_url=urljoin(base, href),
                source_url=source_url,
            ))
        return out

    def parse_html(self, html: str, source_url: str | None = None) -> list[RawVacancy]:
        jobs = self.parse_jsonld(html, source_url)
        if not jobs:
            jobs = self.parse_links(html, source_url)
        return jobs

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        resp = client.get(source.url)
        resp.raise_for_status()
        return self.parse_html(resp.text, source_url=str(resp.url))
