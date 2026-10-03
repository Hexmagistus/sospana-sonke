"""Cornerstone OnDemand (CSOD) career site, e.g. the Transnet talent portal.

The career site is a single-page app, but its first response already carries
``csod.context`` with the anonymous visitor token (``"user": -100``) and the
API base the page itself calls. The token's own claim list names
``rec-job-search/external`` as an endpoint it may use. The page POSTs
``{cloud}/rec-job-search/external/jobs`` with that token to fill its list, and
this strategy sends the same request. No login, no CAPTCHA, no cookie.

``totalCount`` is the real board size. If the pages we could read do not add
up to it, the scan fails instead of storing a partial list as the count.

robots.txt on ``*.csod.com`` allows the page and sets ``Crawl-delay: 10``.
A scan makes one page request plus one API request per 25 roles, and these
boards are not in the hourly "fast" set, so they are read every six hours.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import quote, urlparse

import httpx

from app.scraper.base import RawVacancy, ScrapeStrategy
from app.scraper.politeness import request_with_backoff

_PAGE_SIZE = 25
_MAX_PAGES = 10
_CONTEXT = re.compile(r"csod\.context\s*=\s*(\{.*?\});\s*</script>", re.DOTALL)


def _is_csod_host(host: str) -> bool:
    return host == "csod.com" or host.endswith(".csod.com")


def career_site_ref(url: str) -> tuple[str | None, str | None]:
    """(host, career site id) from ``/ux/ats/careersite/{id}/...``."""
    parsed = urlparse(url)
    match = re.search(r"/ux/ats/careersite/(\d+)", parsed.path)
    host = (parsed.hostname or "").lower()
    if not match or not _is_csod_host(host):
        return None, None
    return host, match.group(1)


def _context(page: str) -> dict:
    match = _CONTEXT.search(page)
    if not match:
        raise ValueError("Cornerstone page has no csod.context")
    try:
        ctx = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError("Cornerstone csod.context is not readable") from exc
    if not isinstance(ctx, dict) or not ctx.get("token"):
        raise ValueError("Cornerstone page gave no visitor token")
    return ctx


def _api_base(ctx: dict, host: str) -> str:
    cloud = ((ctx.get("endpoints") or {}).get("cloud") or "").strip()
    parsed = urlparse(cloud)
    api_host = (parsed.hostname or "").lower()
    # The token is only for Cornerstone's own API. Never send it elsewhere.
    if parsed.scheme != "https" or not _is_csod_host(api_host):
        raise ValueError("Cornerstone API host is not a csod.com host")
    return f"https://{api_host}"


def _iso(value) -> str | None:
    """CSOD dates are M/D/YYYY. normalize_date reads D/M/YYYY, so convert here."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def _location(req: dict) -> str | None:
    seen: list[str] = []
    for loc in req.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        label = ", ".join(str(loc[k]) for k in ("city", "state", "country") if loc.get(k))
        if label and label not in seen:
            seen.append(label)
    return "; ".join(seen) or None


def _to_raw(req: dict, *, host: str, site_id: str, corp: str | None) -> RawVacancy | None:
    title = str(req.get("displayJobTitle") or "").strip()
    req_id = req.get("requisitionId")
    if not title or req_id is None:
        return None
    link = f"https://{host}/ux/ats/careersite/{site_id}/home/requisition/{quote(str(req_id))}"
    link += f"?c={quote(corp or host.split('.')[0])}"
    return RawVacancy(
        title=title,
        external_id=str(req_id),
        location=_location(req),
        posting_date=_iso(req.get("postingEffectiveDate")),
        closing_date=_iso(req.get("postingExpirationDate")),
        description=(str(req.get("externalDescription") or "").strip() or None),
        application_url=link,
        source_url=link,
        raw={"requisitionId": req_id, "title": title},
    )


class CornerstoneStrategy(ScrapeStrategy):
    ats_type = "cornerstone"

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        cfg = source.config or {}
        host, site_id = career_site_ref(source.url)
        host = cfg.get("host") or host
        site_id = cfg.get("career_site_id") or site_id
        if not (host and site_id):
            raise ValueError("Cornerstone source is missing a host or career site id.")
        page = request_with_backoff(client, source.url)
        page.raise_for_status()
        ctx = _context(page.text)
        base = _api_base(ctx, host)
        corp = ctx.get("corp") if isinstance(ctx.get("corp"), str) else None
        endpoint = f"{base}/rec-job-search/external/jobs"
        headers = {"Authorization": f"Bearer {ctx['token']}", "Accept": "application/json"}

        out: dict[str, RawVacancy] = {}
        total: int | None = None
        for number in range(1, _MAX_PAGES + 1):
            resp = request_with_backoff(
                client, endpoint, method="POST", headers=headers,
                json_body={
                    "careerSiteId": int(site_id), "careerSitePageId": int(site_id),
                    "pageNumber": number, "pageSize": _PAGE_SIZE,
                    "cultureId": 1, "cultureName": "en-US", "searchText": "",
                    "states": [], "countryCodes": [], "cities": [], "placeID": "",
                    "radius": None, "postingsWithinDays": None,
                    "customFieldCheckboxKeys": [], "customFieldDropdowns": [],
                    "customFieldRadios": [],
                },
            )
            resp.raise_for_status()
            data = (resp.json() or {}).get("data")
            if not isinstance(data, dict) or not isinstance(data.get("requisitions"), list):
                raise ValueError("Cornerstone search response had no requisition list")
            if total is None:
                count = data.get("totalCount")
                if not isinstance(count, int) or count < 0:
                    raise ValueError("Cornerstone search response had no totalCount")
                total = count
            reqs = data["requisitions"]
            for req in reqs:
                raw = _to_raw(req, host=host, site_id=site_id, corp=corp) \
                    if isinstance(req, dict) else None
                if raw is not None:
                    out.setdefault(raw.external_id, raw)
            if not reqs or len(out) >= total:
                break
        if len(out) != total:
            raise ValueError(
                f"Cornerstone listed {total} roles but only {len(out)} could be read")
        return list(out.values())
