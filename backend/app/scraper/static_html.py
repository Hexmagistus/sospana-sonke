"""Static-HTML strategy: read vacancies from a server-rendered careers page.

Two passes, in order of reliability:
1. schema.org JobPosting JSON-LD (a web standard) — most reliable when present.
2. A heuristic link extractor for plain-HTML job lists (e.g. SANParks, SITA,
   SANRAL): anchors that point at a job detail/PDF and whose text reads like a
   role title. JavaScript-rendered portals return nothing here (correctly) and
   are left for the browser strategy / direct link.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx

from app.scraper.base import ScrapeStrategy, RawVacancy
from app.scraper.jsonld import parse_job_postings
from app.scraper.politeness import is_aws_waf_challenge, request_with_backoff


class BotChallengeError(Exception):
    """The host returned a bot-challenge page, not a vacancy list."""

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
_FEED_LINK = re.compile(
    r'<link\b[^>]*type=["\']application/(?:rss|atom)\+xml["\'][^>]*>',
    re.I,
)
_HREF = re.compile(r'href=["\']([^"\']+)["\']', re.I)
_ITEM = re.compile(r'<(?:item|entry)\b[^>]*>(.*?)</(?:item|entry)>', re.I | re.S)
_TITLE = re.compile(r'<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', re.I | re.S)
_LINK = re.compile(r'<link[^>]*>([^<]+)</link>|<link\b[^>]*href=["\']([^"\']+)["\']', re.I)
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


class StaticHTMLStrategy(ScrapeStrategy):
    ats_type = "static"

    def parse_jsonld(self, html: str, source_url: str | None = None) -> list[RawVacancy]:
        return parse_job_postings(html, source_url)

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

    def feed_href(self, html: str, source_url: str | None = None) -> str | None:
        for tag in _FEED_LINK.findall(html):
            match = _HREF.search(tag)
            if match:
                return urljoin(source_url or "", match.group(1))
        return None

    def parse_feed(self, xml: str, source_url: str | None = None) -> list[RawVacancy]:
        out: list[RawVacancy] = []
        seen: set[str] = set()
        for block in _ITEM.findall(xml):
            title_match = _TITLE.search(block)
            title = _clean_text(title_match.group(1)) if title_match else ""
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            link_match = _LINK.search(block)
            href = ""
            if link_match:
                href = (link_match.group(1) or link_match.group(2) or "").strip()
            out.append(RawVacancy(
                title=title[:300],
                application_url=urljoin(source_url or "", href) if href else source_url,
                source_url=source_url,
            ))
        return out

    def parse_html(self, html: str, source_url: str | None = None) -> list[RawVacancy]:
        jobs = self.parse_jsonld(html, source_url)
        if not jobs:
            jobs = self.parse_links(html, source_url)
        return jobs

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        resp = request_with_backoff(client, source.url)
        if is_aws_waf_challenge(resp.status_code, resp.text):
            raise BotChallengeError(source.url)
        resp.raise_for_status()
        html = resp.text
        final = str(resp.url)
        jobs = self.parse_html(html, source_url=final)
        if jobs:
            return jobs
        feed = self.feed_href(html, final)
        if not feed or feed == final:
            return jobs
        feed_resp = request_with_backoff(client, feed)
        if feed_resp.status_code >= 400:
            return jobs
        return self.parse_feed(feed_resp.text, source_url=final) or jobs
