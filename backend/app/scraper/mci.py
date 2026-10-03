"""MCI Direct Hire career sites (``*.mcidirecthire.com``).

South African state bodies and listed companies share this ATS (ARC, SACAA,
SANSA, SAMRC, Wesgro, Magalies Water, NECSA, TCTA, Growthpoint and others).
There are two page generations. Both fill the job list from a public
anonymous request that the page itself makes; there is no login or CAPTCHA.

* "vacancy" generation (``/Vacancy``): ``GET /Vacancy/Vacancies?PageNumber=n``
  returns card HTML. An empty body is the site's own "No Vacancies Found";
  ``twbsPagination({totalPages: N})`` says how many pages there are.
* "external" generation (``/External/CurrentOpportunities``): the page
  auto-submits ``#ExternalJobSearchForm`` (``POST /External/Search1``).
  ``var ListCounter = N`` is the board size; pages of ten are asked for with
  ``pageNum``.

The other ``jobs.mcidirecthire.com`` "Job Central" site is a different
product and is not handled here. If a page matches neither generation, or the
roles read do not add up to the total the page states, the scan fails and
the card stays "Not counted yet".
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from urllib.parse import urlencode, urljoin, urlparse

import httpx

from app.scraper.base import RawVacancy, ScrapeStrategy
from app.scraper.politeness import request_with_backoff

_MAX_PAGES = 20
_VACANCY_PATH = "/Vacancy"
_EXTERNAL_PATH = "/External/CurrentOpportunities"

_TAGS = re.compile(r"<[^>]+>")
_TOTAL_PAGES = re.compile(r"totalPages:\s*(\d+)")
_LIST_COUNTER = re.compile(r"var\s+ListCounter\s*=\s*(\d+)\s*;")
_CARD_SPLIT = re.compile(r'<div class="card job-card">')
_TITLE = re.compile(r'<strong class="job-title">(.*?)</strong>', re.DOTALL)
_CARD_DATE = re.compile(r'fa-calendar"></i>\s*(\d{4}/\d{2}/\d{2})')
_CARD_PLACE = re.compile(r'fa-map-marker"></i>\s*([^<]+)')
_REF = re.compile(r"Job Reference #:</b>\s*([^<\n]+)")
_DEPT = re.compile(r"<b class=\"text-dh\">Department:</b>\s*([^<]+)")
_UNIT = re.compile(r"<b class=\"text-dh\">Business Unit:</b>\s*([^<]+)")
_POSITIONS = re.compile(r"Positions Available:</b>\s*(\d+)")
_DETAIL = re.compile(r'data-url="([^"]*?/Vacancy/ViewDetails\?parameters=[^"]+)"')
_INTRO = re.compile(r"</b>\s*\d+\s*<br\s*/>\s*<br\s*/>\s*(.*?)</p>", re.DOTALL)
_PANEL_SPLIT = re.compile(r'<div class="paging-container page-\d+"')
_JOB_LABEL = re.compile(r'class="JobTitleLabel"\s+data-jid="(\d+)">(.*?)</span>', re.DOTALL)
_EXT_PLACE = re.compile(r'fa-map-marker\s*"></span>\s*<b>(.*?)</b>', re.DOTALL)
_EXT_DATE = re.compile(r'fa-calendar\s*"></span>\s*<b>(\d{4}/\d{2}/\d{2})</b>')
_EXT_BODY = re.compile(r'synopsis-row">\s*<div[^>]*>\s*(.*?)\s*</div>', re.DOTALL)
_EXT_DETAIL = re.compile(r'data-url="([^"]*?/External/Job\?ref=[^"]+)"')
_FORM = re.compile(r'<form\b[^>]*id="ExternalJobSearchForm"[^>]*>(.*?)</form>', re.DOTALL)
_FORM_ACTION = re.compile(r'<form\b[^>]*id="ExternalJobSearchForm"[^>]*action="([^"]+)"')
_FORM_ACTION_ALT = re.compile(r'<form\b[^>]*action="([^"]+)"[^>]*id="ExternalJobSearchForm"')
_INPUT = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r'\b(type|name|value)="([^"]*)"')
_SELECT = re.compile(r'<select\b[^>]*name="([^"]+)"')


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", fragment))).strip()


def _iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y/%m/%d").date().isoformat()
    except ValueError:
        return None


def _first(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return _plain(match.group(1)) or None


def generation(page: str) -> str | None:
    if "vacancyResultsContainer" in page and "/Vacancy" in page:
        return "vacancy"
    if 'id="ExternalJobSearchForm"' in page:
        return "external"
    return None


# ---- "vacancy" generation ---------------------------------------------------

def parse_vacancy_cards(body: str, origin: str) -> list[RawVacancy]:
    out: list[RawVacancy] = []
    for chunk in _CARD_SPLIT.split(body)[1:]:
        title = _first(_TITLE, chunk)
        if not title:
            continue
        link = _DETAIL.search(chunk)
        url = html.unescape(link.group(1)) if link else None
        ref = _first(_REF, chunk)
        intro = _INTRO.search(chunk)
        extras = [_first(_UNIT, chunk), _first(_DEPT, chunk)]
        out.append(RawVacancy(
            title=title,
            external_id=ref,
            department=", ".join(x for x in extras if x) or None,
            location=_first(_CARD_PLACE, chunk),
            posting_date=_iso(_first(_CARD_DATE, chunk)),
            description=_plain(intro.group(1)) if intro else None,
            application_url=url,
            source_url=url,
            raw={"title": title, "ref": ref, "positions": _first(_POSITIONS, chunk)},
        ))
    return out


def _fetch_vacancy_generation(client: httpx.Client, origin: str) -> list[RawVacancy]:
    out: dict[str, RawVacancy] = {}
    pages = 1
    number = 1
    while number <= min(pages, _MAX_PAGES):
        query = urlencode([
            ("PageNumber", number), ("GroupID", 0), ("EncryptedGroupName", ""),
            ("JobTitle", ""), ("LocationID", ""), ("PSN", ""), ("IndustryID", ""),
            ("DepartmentID", ""), ("BusinessUnitID", ""),
        ])
        resp = request_with_backoff(client, f"{origin}/Vacancy/Vacancies?{query}")
        resp.raise_for_status()
        body = resp.text
        if not body.strip():
            # The site's own "No Vacancies Found". Only a first page can be a true zero.
            if number == 1:
                return []
            raise ValueError("MCI vacancy page came back empty part-way through the list")
        found = _TOTAL_PAGES.search(body)
        if found is None:
            raise ValueError("MCI vacancy list did not say how many pages there are")
        pages = max(1, int(found.group(1)))
        if pages > _MAX_PAGES:
            raise ValueError("MCI vacancy list has more pages than we read")
        cards = parse_vacancy_cards(body, origin)
        if not cards:
            raise ValueError("MCI vacancy page had no readable cards")
        for card in cards:
            out.setdefault(card.external_id or card.title, card)
        number += 1
    return list(out.values())


# ---- "external" generation --------------------------------------------------

def parse_external_cards(body: str) -> list[RawVacancy]:
    out: list[RawVacancy] = []
    for chunk in _PANEL_SPLIT.split(body)[1:]:
        label = _JOB_LABEL.search(chunk)
        if not label:
            continue
        title = _plain(label.group(2))
        if not title:
            continue
        job_id = label.group(1)
        link = _EXT_DETAIL.search(chunk)
        url = html.unescape(link.group(1)) if link else None
        body_text = _EXT_BODY.search(chunk)
        out.append(RawVacancy(
            title=title,
            external_id=job_id,
            location=_first(_EXT_PLACE, chunk),
            posting_date=_iso(_first(_EXT_DATE, chunk)),
            description=_plain(body_text.group(1)) if body_text else None,
            application_url=url,
            source_url=url,
            raw={"id": job_id, "title": title},
        ))
    return out


def _form_fields(page: str, page_url: str) -> tuple[str, dict[str, str]]:
    form = _FORM.search(page)
    action = _FORM_ACTION.search(page) or _FORM_ACTION_ALT.search(page)
    if not form or not action:
        raise ValueError("MCI search form not found")
    target = urljoin(page_url, html.unescape(action.group(1)))
    fields: dict[str, str] = {}
    for tag in _INPUT.findall(form.group(1)):
        attrs = dict(_ATTR.findall(tag))
        if attrs.get("type", "text").lower() in ("hidden", "text") and attrs.get("name"):
            fields[attrs["name"]] = html.unescape(attrs.get("value", ""))
    for name in _SELECT.findall(form.group(1)):
        fields.setdefault(name, "")
    return target, fields


def _fetch_external_generation(client: httpx.Client, page: str, page_url: str) -> list[RawVacancy]:
    action, fields = _form_fields(page, page_url)
    if _host(action) != _host(page_url):
        raise ValueError("MCI search form posts to a different host")
    out: dict[str, RawVacancy] = {}
    total: int | None = None
    number = 1
    while number <= _MAX_PAGES:
        resp = request_with_backoff(client, action, method="POST",
                                    form_body={**fields, "pageNum": str(number)})
        resp.raise_for_status()
        counter = _LIST_COUNTER.search(resp.text)
        if counter is None:
            raise ValueError("MCI search response did not state a total")
        if total is None:
            total = int(counter.group(1))
            if total == 0:
                return []
        cards = parse_external_cards(resp.text)
        if not cards:
            break
        for card in cards:
            out.setdefault(card.external_id or card.title, card)
        if len(out) >= total:
            break
        number += 1
    if total is None or len(out) != total:
        raise ValueError(f"MCI listed {total} roles but {len(out)} could be read")
    return list(out.values())


class MciStrategy(ScrapeStrategy):
    ats_type = "mci"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        parsed = urlparse(source.url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            raise ValueError("MCI source needs an https URL")
        origin = f"https://{parsed.netloc}"
        tried: list[str] = []
        for url in (source.url, origin + _VACANCY_PATH, origin + _EXTERNAL_PATH):
            if url in tried or len(tried) >= 3:
                continue
            tried.append(url)
            resp = request_with_backoff(client, url)
            if resp.status_code >= 400:
                continue
            final = str(resp.url)
            if _host(final) != host:
                raise ValueError("MCI board redirected to a different host")
            kind = generation(resp.text)
            if kind == "vacancy":
                return _fetch_vacancy_generation(client, origin)
            if kind == "external":
                return _fetch_external_generation(client, resp.text, final)
        raise ValueError("MCI Direct Hire page has no vacancy list we can read")
