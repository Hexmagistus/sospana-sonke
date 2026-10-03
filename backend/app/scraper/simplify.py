"""simplify.hr company career sites (``{company}.simplify.hr``).

The home page is a shell. Its own script (``/bundles/company``) fills the
"Current Vacancies" box from ``GET /vacancy/vacancies?query=&displayOrder=N``,
which returns an HTML fragment. ``displayOrder`` is the ``data-order`` on the
page's search button and only changes how the fragment is grouped. No login,
no CAPTCHA. robots.txt only disallows ``/Vacancy/Apply/*``, which is not
fetched here.

An empty board answers with the site's own sentence "There are currently no
open jobs listed". That is a real zero. A fragment with neither roles nor that
sentence is a failure, never a zero.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import httpx

from app.scraper.base import RawVacancy, ScrapeStrategy
from app.scraper.politeness import request_with_backoff

_ORDER = re.compile(r'id="search"[^>]*\bdata-order="(\d+)"')
_NONE = re.compile(r"there\s+are\s+currently\s+no\s+open\s+jobs", re.IGNORECASE)
# Most tenants link "/Vacancy/{id}"; the IIE group's tenants link the absolute
# "https://{tenant}.Simplify.hr/Vacancy/{id}". Both are the same board.
_TITLE = re.compile(r'<div class="row job-title">\s*<a href="(?:https?://[A-Za-z0-9.-]+)?(/Vacancy/(\d+))">(.*?)</a>',
                    re.DOTALL | re.IGNORECASE)
_PLACE = re.compile(r'<span class="fa fa-map-marker"></span>\s*([^<]+)')
_PUBLISHED = re.compile(r"Published\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})")
_CLOSING = re.compile(r"Closing Date:\s*<b>\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*</b>")
_TAGS = re.compile(r"<[^>]+>")


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", fragment))).strip()


def parse_vacancies(fragment: str, origin: str) -> list[RawVacancy]:
    matches = list(_TITLE.finditer(fragment))
    out: list[RawVacancy] = []
    seen: set[str] = set()
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(fragment)
        chunk = fragment[match.end():end]
        job_id = match.group(2)
        title = _plain(match.group(3))
        if not title or job_id in seen:
            continue
        seen.add(job_id)
        place = _PLACE.search(chunk)
        published = _PUBLISHED.search(chunk)
        closing = _CLOSING.search(chunk)
        link = f"{origin}{match.group(1)}"
        out.append(RawVacancy(
            title=title,
            external_id=job_id,
            location=_plain(place.group(1)) if place else None,
            posting_date=published.group(1) if published else None,
            closing_date=closing.group(1) if closing else None,
            application_url=link,
            source_url=link,
            raw={"id": job_id, "title": title},
        ))
    return out


class SimplifyStrategy(ScrapeStrategy):
    ats_type = "simplify"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        parsed = urlparse(source.url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host.endswith(".simplify.hr"):
            raise ValueError("simplify.hr source needs an https company host")
        origin = f"https://{parsed.netloc}"
        home = request_with_backoff(client, origin + "/")
        home.raise_for_status()
        if (urlparse(str(home.url)).hostname or "").lower() != host:
            raise ValueError("simplify.hr board redirected to a different host")
        if 'id="companyVacanciesResultsContainer"' not in home.text:
            raise ValueError("simplify.hr page has no vacancy list")
        order = _ORDER.search(home.text)
        listing = request_with_backoff(
            client, f"{origin}/vacancy/vacancies?query=&displayOrder={order.group(1) if order else 0}")
        listing.raise_for_status()
        rows = parse_vacancies(listing.text, origin)
        if rows:
            return rows
        if _NONE.search(listing.text):
            return []
        raise ValueError("simplify.hr vacancy list was not readable")
