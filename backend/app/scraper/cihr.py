"""CareerInHR public job search (``*.ci.hr``).

The job-search page does not list the roles. It declares a ``List`` widget,
then the page itself GETs ``index.php?controller=Listings&method=get``.
The same HTTP client is reused so the anonymous session cookie from the
first response goes with that GET. This is the public listing the careers
page loads. It does not log in and it does not solve a CAPTCHA.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlencode, urljoin, urlparse

import httpx

from app.scraper.base import RawVacancy, ScrapeStrategy
from app.scraper.politeness import request_with_backoff

_MAX_BATCHES = 20
_MAX_BATCH_SIZE = 100
_LIST_BLOCK = re.compile(r"new\s+List\s*\(\s*\{(.*?)\}\s*\)", re.DOTALL)
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_CARD_START = re.compile(
    r'<div\s+class="dynamic-card view-data-row[^"]*"\s+id="([0-9a-fA-F-]{36})"',
    re.IGNORECASE,
)
_TITLE = re.compile(
    r"""<h5[^>]*>\s*<a\s+[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""",
    re.IGNORECASE | re.DOTALL,
)
_RECORDCOUNT = re.compile(r'data-recordcount="(\d+)"', re.IGNORECASE)
_PARA = re.compile(r"<p>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_TAGS = re.compile(r"<[^>]+>")


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _js_string(body: str, key: str) -> str | None:
    match = re.search(rf'\b{re.escape(key)}\s*:\s*"([^"]*)"', body)
    if match:
        return match.group(1)
    match = re.search(rf"\b{re.escape(key)}\s*:\s*'([^']*)'", body)
    return match.group(1) if match else None


def _js_int(body: str, key: str) -> int | None:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*(\d+)", body)
    return int(match.group(1)) if match else None


def _parse_widget(page: str) -> dict | None:
    """The listings widget the job-search page itself uses. None if absent."""
    found = None
    for match in _LIST_BLOCK.finditer(page):
        body = match.group(1)
        entity = (_js_string(body, "entity") or "").lower()
        if entity != "listings":
            continue
        size = _js_int(body, "batchsize") or 10
        widget = {
            "controller": _js_string(body, "controller") or "List",
            "endpoint": _js_string(body, "endpoint") or "retrieve",
            "view_id": _js_string(body, "viewId"),
            "batchsize": max(1, min(size, _MAX_BATCH_SIZE)),
        }
        adapter = _js_string(body, "adapter")
        if adapter is not None:
            widget["adapter"] = adapter
        if _js_string(body, "id") == "listings-list":
            return widget
        found = widget
    return found


def _jobsearch_url(page: str, page_url: str) -> str | None:
    """One same-host link to the job-search page. Featured cards are not it."""
    page_host = _host(page_url)
    for match in _HREF.finditer(page):
        href = html.unescape(match.group(1)).replace("&amp;", "&")
        low = href.lower()
        if "controller=page" not in low or "name=jobsearch" not in low:
            continue
        absolute = urljoin(page_url, href)
        if _host(absolute) == page_host:
            return absolute
    return None


def _plain(fragment: str) -> str:
    text = _TAGS.sub(" ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _labeled(chunk: str, label: str) -> str | None:
    match = re.search(
        rf"<b>\s*{re.escape(label)}\s*:?\s*</b>\s*:?\s*([^<]+)",
        chunk,
        re.IGNORECASE,
    )
    if not match:
        return None
    value = html.unescape(match.group(1)).strip()
    return value or None


def _list_url(page_url: str, widget: dict, batch: int) -> str:
    params = [
        ("controller", widget["controller"]),
        ("method", widget["endpoint"]),
        ("entity", "listings"),
        ("wrap", "false"),
        ("batch", str(batch)),
        ("batchsize", str(widget["batchsize"])),
    ]
    if widget.get("view_id"):
        params.append(("viewid", widget["view_id"]))
    if "adapter" in widget:
        params.append(("adapter", widget["adapter"]))
    return urljoin(page_url, "?" + urlencode(params))


def _parse_cards(body: str, page_url: str) -> tuple[int | None, list[RawVacancy]]:
    count_match = _RECORDCOUNT.search(body)
    count = int(count_match.group(1)) if count_match else None
    starts = list(_CARD_START.finditer(body))
    rows: list[RawVacancy] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        chunk = body[start.start():end]
        title_match = _TITLE.search(chunk)
        if not title_match:
            continue
        title = _plain(title_match.group(2))
        if not title:
            continue
        external_id = start.group(1)
        application_url = urljoin(page_url, html.unescape(title_match.group(1)))
        paragraph = _PARA.search(chunk)
        rows.append(RawVacancy(
            title=title,
            external_id=external_id,
            department=_labeled(chunk, "Job category"),
            location=_labeled(chunk, "Location"),
            employment_type=_labeled(chunk, "Contract type"),
            salary=_labeled(chunk, "Remuneration"),
            closing_date=_labeled(chunk, "Apply by"),
            description=_plain(paragraph.group(1)) if paragraph else None,
            application_url=application_url,
            source_url=application_url,
            raw={"id": external_id, "title": title},
        ))
    return count, rows


class CihrStrategy(ScrapeStrategy):
    ats_type = "cihr"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        page_url, page = _page_with_widget(client, source.url)
        widget = _parse_widget(page)
        if widget is None:
            raise ValueError("ci.hr page has no listings widget")
        return _collect(client, page_url, widget)


def _fetch_same_host(client: httpx.Client, url: str) -> tuple[str, str]:
    resp = request_with_backoff(client, url)
    resp.raise_for_status()
    final = str(resp.url)
    if _host(final) != _host(url):
        raise ValueError("ci.hr board redirected to a different host")
    return final, resp.text


def _page_with_widget(client: httpx.Client, url: str, hops: int = 1) -> tuple[str, str]:
    final, page = _fetch_same_host(client, url)
    if _parse_widget(page) is not None:
        return final, page
    if hops <= 0:
        raise ValueError("ci.hr page has no listings widget")
    hop = _jobsearch_url(page, final)
    if not hop:
        raise ValueError("ci.hr page has no listings widget")
    return _page_with_widget(client, hop, hops=0)


def _collect(client: httpx.Client, page_url: str, widget: dict) -> list[RawVacancy]:
    seen: dict[str, RawVacancy] = {}
    order: list[str] = []
    recordcount: int | None = None
    for batch in range(1, _MAX_BATCHES + 1):
        list_url = _list_url(page_url, widget, batch)
        if _host(list_url) != _host(page_url):
            raise ValueError("ci.hr board redirected to a different host")
        final, body = _fetch_same_host(client, list_url)
        count, rows = _parse_cards(body, final)
        if count is None and not rows:
            if batch == 1 and not order:
                raise ValueError("ci.hr listings response had no job list")
            break
        if count == 0 and not rows:
            return [] if not order else [seen[i] for i in order]
        if count is not None:
            recordcount = count
        added = 0
        for row in rows:
            key = row.external_id or row.title
            if key in seen:
                continue
            seen[key] = row
            order.append(key)
            added += 1
        if added == 0:
            break
        if recordcount is None or len(order) >= recordcount:
            break
    return [seen[i] for i in order]
