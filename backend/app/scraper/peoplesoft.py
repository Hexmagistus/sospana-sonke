"""Oracle PeopleSoft HCM "Careers" (HRS_HRAM_FL), e.g. candidate.csir.co.za.

The public Careers page is the guest search component. It renders no roles
until its own Search button is pressed, which posts the page's form back with
``ICAction=HRS_SCH_WRK_FLU_HRS_SEARCH_BTN`` and an empty keyword. That is
all this strategy does: the same anonymous session (cookie kept by the HTTP
client), the same hidden fields, no login and no CAPTCHA.

PeopleSoft refuses a client whose user agent it does not recognise with an
"Unsupported Browser" page, so these two requests send a browser-style agent
that still names the bot.

``N jobs found`` is the board size. If it is missing, or the rows on the page
do not match it, the scan fails instead of storing a partial count.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlencode, urljoin, urlparse

import httpx

from app.scraper.base import RawVacancy, ScrapeStrategy
from app.scraper.politeness import request_with_backoff

SEARCH_PATH = "/psp/hr/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?FOCUS=Applicant"
_SEARCH_BUTTON = "HRS_SCH_WRK_FLU_HRS_SEARCH_BTN"
_KEYWORD_FIELD = "HRS_SCH_WRK_HRS_SCH_TEXT100$0"
_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0 SospanaSonkeBot/0.1"

_FORM = re.compile(r"<form\b[^>]*name=['\"]win0['\"][^>]*>", re.IGNORECASE)
_ACTION = re.compile(r"""action\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_INPUT = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""\b(type|name|value)\s*=\s*(?:'([^']*)'|"([^"]*)")""", re.IGNORECASE)
_VALUE = re.compile(
    r"""<span\s+class=['"]ps_box-value['"]\s+id=['"]([A-Z_0-9]+)\$(\d+)['"]\s*>(.*?)</span>""",
    re.IGNORECASE | re.DOTALL,
)
_FOUND = re.compile(r"<b>\s*(\d+)\s*</b>\s*jobs?\s+found", re.IGNORECASE)
_NONE_FOUND = re.compile(r"\bno\s+(?:matching\s+)?jobs?\s+found\b", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")


def is_peoplesoft_careers(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path
    if "HRS_HRAM_FL" in path and re.search(r"/ps[pc]/", path):
        return True
    return host == "candidate.csir.co.za"


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", fragment))).strip()


def _form_fields(page: str, page_url: str) -> tuple[str, dict[str, str]]:
    form = _FORM.search(page)
    if not form:
        raise ValueError("PeopleSoft careers page has no search form")
    action = _ACTION.search(form.group(0))
    target = urljoin(page_url, html.unescape(action.group(1))) if action else page_url
    fields: dict[str, str] = {}
    for tag in _INPUT.findall(page):
        attrs = {m.group(1).lower(): m.group(2) if m.group(2) is not None else m.group(3)
                 for m in _ATTR.finditer(tag)}
        if (attrs.get("type") or "").lower() == "hidden" and attrs.get("name"):
            fields[attrs["name"]] = html.unescape(attrs.get("value") or "")
    if "ICSID" not in fields or "ICStateNum" not in fields:
        raise ValueError("PeopleSoft careers form has no session fields")
    return target, fields


def _deep_link(page_url: str, job_id: str) -> str:
    base = page_url.split("?", 1)[0]
    query = urlencode([("Page", "HRS_APP_JBPST_FL"), ("Action", "U"), ("FOCUS", "Applicant"),
                       ("SiteId", "1"), ("JobOpeningId", job_id), ("PostingSeq", "1")])
    return f"{base}?{query}"


def parse_results(page: str, page_url: str) -> list[RawVacancy]:
    declared = _FOUND.search(page)
    rows: dict[str, dict[str, str]] = {}
    for name, index, inner in _VALUE.findall(page):
        rows.setdefault(index, {})[name] = _plain(inner)
    vacancies: list[RawVacancy] = []
    for index in sorted(rows, key=int):
        row = rows[index]
        title = row.get("SCH_JOB_TITLE", "")
        job_id = row.get("HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID", "")
        if not title or not job_id:
            continue
        link = _deep_link(page_url, job_id)
        vacancies.append(RawVacancy(
            title=title,
            external_id=job_id,
            department=row.get("HRS_APP_JBSCH_I_HRS_DEPT_DESCR") or None,
            location=row.get("LOCATION") or None,
            posting_date=row.get("SCH_OPENED") or None,
            closing_date=row.get("HRS_CLS_DT_DESCR") or None,
            application_url=link,
            source_url=link,
            raw={"id": job_id, "title": title, "cluster": row.get("HRS_BU_DESCR")},
        ))
    if declared is not None:
        if int(declared.group(1)) != len(vacancies):
            raise ValueError(
                f"PeopleSoft listed {declared.group(1)} jobs but {len(vacancies)} could be read")
        return vacancies
    if not vacancies and _NONE_FOUND.search(page):
        return []
    raise ValueError("PeopleSoft results page did not say how many jobs were found")


class PeopleSoftStrategy(ScrapeStrategy):
    ats_type = "peoplesoft"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        parsed = urlparse(source.url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            raise ValueError("PeopleSoft source needs an https URL")
        if "HRS_HRAM_FL" in parsed.path and re.search(r"/ps[pc]/", parsed.path):
            start = source.url
        else:
            start = f"https://{parsed.netloc}{SEARCH_PATH}"
        headers = {"User-Agent": _UA}
        resp = request_with_backoff(client, start, headers=headers)
        resp.raise_for_status()
        page_url = str(resp.url)
        if (urlparse(page_url).hostname or "").lower() != host:
            raise ValueError("PeopleSoft board redirected to a different host")
        action, fields = _form_fields(resp.text, page_url)
        if (urlparse(action).hostname or "").lower() != host:
            raise ValueError("PeopleSoft form posts to a different host")
        fields.update({"ICAction": _SEARCH_BUTTON, _KEYWORD_FIELD: ""})
        result = request_with_backoff(client, action, method="POST", headers=headers,
                                      form_body=fields)
        result.raise_for_status()
        return parse_results(result.text, action)
