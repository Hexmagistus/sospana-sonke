"""iCIMS career portals (Discovery, Toyota SA, Mediclinic, AECI, and others).

The public search page is server-rendered HTML. A portal bookmark looks like
``/go/<name>/<id>/`` (sometimes under a country prefix, as on Mediclinic) or
a search URL that carries the portal's own ``createNewAlert=false`` field.
robots.txt on these hosts allows those pages. It disallows ``/services/``,
which this parser does not request.

Each page states a total (``Results 1 – 25 of 59``) and links the next page.
The list date is the posting date (the column sorts by ``referencedate``),
not a closing date. A page that says there are no open positions is a real
zero, including when it then lists other roles "for your convenience".
Those rows are not the search result. A page we cannot reconcile with its
own total is a failure, so a partial first page is never stored as the
whole board.
"""
from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from app.scraper.base import RawVacancy, ScrapeStrategy
from app.scraper.politeness import request_with_backoff
from app.scraper.static_html import BotChallengeError, _is_wait_interstitial

# Eight pages is 200 roles at the usual 25-per-page. Past that the scan
# fails rather than storing a slice and later closing the roles it never saw.
_MAX_PAGES = 8

_NONE = re.compile(
    r"there are currently no open positions|sorry,\s*no jobs were found",
    re.IGNORECASE,
)
_TOTAL = re.compile(r"of\s*<b>\s*([\d,]+)\s*</b>", re.IGNORECASE)
_PAGER = re.compile(r'<ul class="pagination">(.*?)</ul>', re.IGNORECASE | re.DOTALL)
_ANCHOR = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_HREF = re.compile(r"""\bhref=["']([^"']+)["']""", re.IGNORECASE)
_CLASS = re.compile(r"""\bclass=["']([^"']*)["']""", re.IGNORECASE)
_ROW = re.compile(r'<tr class="data-row">(.*?)</tr>', re.IGNORECASE | re.DOTALL)
_DESKTOP_TITLE = re.compile(
    r'<span class="jobTitle hidden-phone">\s*<a\b([^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_COL = re.compile(
    r'<td class="(col[A-Za-z]+)\b[^"]*"[^>]*>(.*?)</td>',
    re.IGNORECASE | re.DOTALL,
)
_POSTED = re.compile(
    r'<span class="jobDate">\s*([^<]+?)\s*</span>',
    re.IGNORECASE,
)
_FACILITY_SPAN = re.compile(
    r'<span class="jobFacility[^"]*">\s*([^<]+?)\s*</span>',
    re.IGNORECASE,
)
_TILE = re.compile(
    r'<li class="job-tile\b([^>]*)>(.*?)</li>',
    re.IGNORECASE | re.DOTALL,
)
_DATA_URL = re.compile(r"""\bdata-url=["']([^"']+)["']""", re.IGNORECASE)
_TITLE_LINK = re.compile(
    r'<a\b([^>]*\bjobTitle-link\b[^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_DESKTOP = re.compile(
    r'class="[^"]*sub-section-desktop[^"]*"[^>]*>(.*?)(?=<div class="[^"]*sub-section-(?:mobile|tablet)|</li>)',
    re.IGNORECASE | re.DOTALL,
)
_LABELED = re.compile(
    r'class="section-label[^"]*"[^>]*>\s*([^<]+?)\s*</span>\s*'
    r'<div id="[^"]*-value">\s*([^<]*?)\s*</div>',
    re.IGNORECASE | re.DOTALL,
)
_RETURNED = re.compile(r"""\bdata-record-returned=["'](\d+)["']""", re.IGNORECASE)
_JOB_ID = re.compile(r"/(\d+)/?$")
_TAGS = re.compile(r"<[^>]+>")


def is_icims_url(url: str) -> bool:
    """True for an iCIMS portal URL, not for a look-alike path."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "icims.com" or host.endswith(".icims.com"):
        return True
    parts = [part for part in (parsed.path or "").split("/") if part]
    if "go" in parts:
        rest = parts[parts.index("go") + 1:]
        if len(rest) >= 2 and rest[0] and rest[1].isdigit():
            return True
    keys = {key.lower() for key in parse_qs(parsed.query)}
    return "createnewalert" in keys


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", fragment))).strip()


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _col(chunk: str, name: str) -> str | None:
    for css, inner in _COL.findall(chunk):
        if css.lower() == name.lower():
            text = _plain(inner)
            if text:
                return text
    return None


def _job_from_link(page_url: str, origin_host: str, href: str, title: str,
                   *, location: str | None, department: str | None,
                   posting_date: str | None) -> RawVacancy | None:
    link = urljoin(page_url, html.unescape(href))
    if _host(link) != origin_host:
        return None
    job_match = _JOB_ID.search(urlparse(link).path)
    title = _plain(title)
    if not job_match or not title:
        return None
    job_id = job_match.group(1)
    return RawVacancy(
        title=title,
        external_id=job_id,
        department=department,
        location=location,
        posting_date=posting_date,
        application_url=link,
        source_url=link,
        raw={"id": job_id, "title": title},
    )


def _table_rows(body: str, page_url: str, origin_host: str) -> list[RawVacancy]:
    rows: list[RawVacancy] = []
    seen: set[str] = set()
    for chunk in _ROW.findall(body):
        title_match = _DESKTOP_TITLE.search(chunk)
        if not title_match:
            continue
        href_match = _HREF.search(title_match.group(1))
        if not href_match:
            continue
        # Some portals put the place in Location, others in Facility, and the
        # category in a shift-type column. The list date is the posting date.
        place = _col(chunk, "colLocation")
        facility_span = _FACILITY_SPAN.search(chunk)
        facility = _col(chunk, "colFacility") or (
            _plain(facility_span.group(1)) if facility_span else None)
        category = _col(chunk, "colShifttype")
        if place:
            department = facility or category
        else:
            place = facility
            department = category
        posted = _POSTED.search(chunk)
        job = _job_from_link(
            page_url, origin_host, href_match.group(1), title_match.group(2),
            location=place, department=department,
            posting_date=_plain(posted.group(1)) if posted else None,
        )
        if job is None or job.external_id in seen:
            continue
        seen.add(job.external_id or "")
        rows.append(job)
    return rows


def _tile_rows(body: str, page_url: str, origin_host: str) -> tuple[list[RawVacancy], bool]:
    """Job tiles, and whether this page says it holds the whole list.

    The tile skin repeats each role for desktop, tablet and phone. The id
    keeps one. ``aria-rowcount`` on that skin is a grid figure, so the page
    is complete when the tile count equals ``data-record-returned`` and it
    links no further page.
    """
    rows: list[RawVacancy] = []
    seen: set[str] = set()
    for attrs, chunk in _TILE.findall(body):
        url_match = _DATA_URL.search(attrs) or _DATA_URL.search(chunk)
        desktop = _DESKTOP.search(chunk)
        scope = desktop.group(1) if desktop else chunk
        title_match = _TITLE_LINK.search(scope) or _TITLE_LINK.search(chunk)
        if not url_match or not title_match:
            continue
        href_match = _HREF.search(title_match.group(1))
        href = href_match.group(1) if href_match else url_match.group(1)
        labels = {label.strip().lower(): _plain(value)
                  for label, value in _LABELED.findall(scope)}
        city = labels.get("city") or labels.get("location") or labels.get("town / city")
        facility = labels.get("facility")
        posted = _POSTED.search(scope)
        job = _job_from_link(
            page_url, origin_host, href, title_match.group(2),
            location=city or facility,
            department=facility if city else None,
            posting_date=_plain(posted.group(1)) if posted else None,
        )
        if job is None or job.external_id in seen:
            continue
        seen.add(job.external_id or "")
        rows.append(job)
    returned = _RETURNED.search(body)
    complete = bool(rows) and returned is not None and int(returned.group(1)) == len(rows)
    return rows, complete


def _next_pages(body: str, page_url: str, origin_host: str) -> list[str]:
    next_urls: list[str] = []
    for pager in _PAGER.findall(body):
        for attrs, _text in _ANCHOR.findall(pager):
            class_match = _CLASS.search(attrs)
            classes = class_match.group(1) if class_match else ""
            if "current-page" in classes:
                continue
            href_match = _HREF.search(attrs)
            if not href_match:
                continue
            link = urljoin(page_url, html.unescape(href_match.group(1)))
            if _host(link) != origin_host or link in next_urls:
                continue
            next_urls.append(link)
    return next_urls


def parse_search_page(body: str, page_url: str) -> tuple[list[RawVacancy], int | None, list[str]]:
    """Rows, the stated total, and same-host links to the other pages."""
    text = body or ""
    total_match = _TOTAL.search(text)
    total = int(total_match.group(1).replace(",", "")) if total_match else None
    origin_host = _host(page_url)
    rows = _table_rows(text, page_url, origin_host)
    next_urls = _next_pages(text, page_url, origin_host)
    if rows:
        return rows, total, next_urls
    tiles, complete = _tile_rows(text, page_url, origin_host)
    if tiles and total is None and complete and not next_urls:
        total = len(tiles)
    return tiles, total, next_urls


def no_positions(body: str) -> bool:
    return bool(_NONE.search(body or ""))


class IcimsStrategy(ScrapeStrategy):
    ats_type = "icims"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        parsed = urlparse(source.url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host or not is_icims_url(source.url):
            raise ValueError("icims source needs an https portal url")
        queue = [source.url]
        seen_pages: set[str] = set()
        jobs: dict[str, RawVacancy] = {}
        total: int | None = None
        last_body = ""
        pages = 0
        while queue and pages < _MAX_PAGES:
            url = queue.pop(0)
            if url in seen_pages:
                continue
            seen_pages.add(url)
            response = request_with_backoff(client, url)
            if response.status_code == 202 and "awswaf" in (response.text or "").lower():
                raise BotChallengeError(url)
            response.raise_for_status()
            final = str(response.url)
            if _host(final) != host:
                raise ValueError("icims board redirected to a different host")
            if _is_wait_interstitial(response.text):
                raise BotChallengeError(url)
            last_body = response.text
            # A missed keyword or place search still prints other roles "for
            # your convenience" and counts those. They are not this search.
            if no_positions(last_body):
                return []
            page_jobs, page_total, next_urls = parse_search_page(last_body, final)
            if page_total is not None:
                total = page_total
            for job in page_jobs:
                if job.external_id and job.external_id not in jobs:
                    jobs[job.external_id] = job
            pages += 1
            for link in next_urls:
                if link not in seen_pages and link not in queue:
                    queue.append(link)
            if total is not None and len(jobs) >= total:
                break
        if not jobs:
            if total == 0 or no_positions(last_body):
                return []
            raise ValueError("icims vacancy list was not readable")
        if total is None or len(jobs) != total:
            raise ValueError("icims vacancy list did not match the stated total")
        return list(jobs.values())
