"""Look for direct careers links on blank seed rows. Offline only.

A hit is kept when robots.txt allows SospanaSonkeBot (or the host has no
robots.txt), the page is HTTP 200, the board is that employer's, and either
at least half of the located roles are in the employer's country or a stable
Workday ``locationCountry`` filter lists at least two roles there.

    python scripts/discover_seed_careers.py --country "United States" --out /tmp/hits.json

``--render`` renders a JavaScript shell when a non-Workday page does not name
a post in the HTTP body. The scan cron does not call this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.seed_board import (
    decide_board,
    decide_counts,
    names_match,
    slug_variants,
    workday_country_facet,
    workday_filter_url,
)
from app.services.seed_page import fetch_seed_page, looks_like_js_shell

UA = settings.URL_TEST_USER_AGENT
_WD_CLUSTERS = (1, 3, 5, 103)
_SKIP_SITES = {"refreshfacet", "wday"}


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": UA, "Accept": "application/json,text/html"},
        follow_redirects=False,
        timeout=httpx.Timeout(12.0, connect=4.0),
    )


def _open(client: httpx.Client, url: str, *, method: str = "GET", body: dict | None = None):
    """SSRF-checked request. robots.txt is enforced on the stored page, not the JSON host."""
    from app.scraper.politeness import request_with_backoff
    return request_with_backoff(
        client, url, retries=1, sleep=lambda _delay: None, method=method, json_body=body,
    )


def _titles_present(html: str, titles: list[str]) -> bool:
    low = (html or "").lower()
    return any(title and title.lower() in low for title in titles[:3])


def _confirm(client, url: str, titles: list[str], *, renderer, workday: bool, filtered: bool) -> str | None:
    page = fetch_seed_page(url, client, renderer=None)
    if page.error == "robots" or page.robots_allowed is False or not page.ok:
        return None
    final = page.final_url or ""
    host = (urlparse(final).hostname or "").lower()
    if workday:
        if "myworkdayjobs.com" not in host:
            return None
        if filtered and "locationcountry=" not in final.lower():
            return None
        return final
    if not _titles_present(page.html, titles) and looks_like_js_shell(page.html) and renderer is not None:
        page = fetch_seed_page(url, client, renderer=renderer)
        if not page.ok:
            return None
        final = page.final_url or final
    if not _titles_present(page.html, titles):
        return None
    return final


def probe_json(client, name: str, country: str, renderer) -> dict | None:
    for slug in slug_variants(name):
        token = slug.replace("-", "")
        hit = _greenhouse(client, name, country, slug, renderer)
        if hit:
            return hit
        hit = _lever(client, name, country, slug, renderer)
        if hit:
            return hit
        hit = _ashby(client, name, country, slug, renderer)
        if hit:
            return hit
        hit = _workable(client, name, country, token, renderer)
        if hit:
            return hit
        hit = _smartrecruiters(client, name, country, token, renderer)
        if hit:
            return hit
        hit = _workday(client, name, country, token, renderer)
        if hit:
            return hit
    return None


def _accept_sample(name, country, board, titles, locations, ats, url, client, renderer, *, allow_filter=False):
    if board:
        if not names_match(name, board):
            return None
    else:
        compact = slug_from_url(url)
        alnum = "".join(ch for ch in name.lower() if ch.isalnum())
        if len(compact) < 5 or compact not in alnum:
            return None
    if len(titles) < 2:
        return None
    decision = decide_board(locations, country)
    if not decision.accept:
        return None
    if decision.filtered and not allow_filter:
        return None
    final = _confirm(client, url, titles, renderer=renderer, workday=ats == "workday", filtered=decision.filtered)
    if not final:
        return None
    return _hit(name, country, ats, final, decision, titles)


def slug_from_url(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return (parts[0] if parts else "").replace("-", "").lower()


def _hit(name, country, ats, url, decision, titles) -> dict:
    return {
        "name": name,
        "country": country,
        "ats": ats,
        "url": url,
        "filtered": decision.filtered,
        "here": decision.here,
        "located": decision.located,
        "share": round(decision.share, 3),
        "titles": [title for title in titles if title][:3],
    }


def _greenhouse(client, name, country, slug, renderer):
    try:
        response = _open(client, f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false")
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    jobs = (response.json() or {}).get("jobs") or []
    titles, locations = [], []
    boards = Counter()
    for job in jobs:
        title = (job.get("title") or "").strip()
        if not title:
            continue
        titles.append(title)
        locations.append(((job.get("location") or {}).get("name") or ""))
        boards[job.get("company_name") or ""] += 1
    board = boards.most_common(1)[0][0] if boards else ""
    return _accept_sample(
        name, country, board, titles, locations, "greenhouse",
        f"https://job-boards.greenhouse.io/{slug}", client, renderer,
    )


def _lever(client, name, country, slug, renderer):
    try:
        response = _open(client, f"https://api.lever.co/v0/postings/{slug}?mode=json")
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    data = response.json()
    if not isinstance(data, list):
        return None
    titles, locations = [], []
    for job in data:
        title = (job.get("text") or "").strip()
        if not title:
            continue
        titles.append(title)
        locations.append(((job.get("categories") or {}).get("location") or ""))
    return _accept_sample(
        name, country, "", titles, locations, "lever",
        f"https://jobs.lever.co/{slug}", client, renderer,
    )


def _ashby(client, name, country, slug, renderer):
    try:
        response = _open(client, f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    jobs = (response.json() or {}).get("jobs") or []
    titles, locations = [], []
    for job in jobs:
        title = (job.get("title") or "").strip()
        if not title:
            continue
        titles.append(title)
        location = job.get("location") or ""
        if isinstance(location, dict):
            location = location.get("name") or ""
        locations.append(str(location))
    return _accept_sample(
        name, country, "", titles, locations, "ashby",
        f"https://jobs.ashbyhq.com/{slug}", client, renderer,
    )


def _workable(client, name, country, token, renderer):
    try:
        response = _open(client, f"https://www.workable.com/api/accounts/{token}?details=true")
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    data = response.json() or {}
    titles, locations = [], []
    for job in data.get("jobs") or []:
        title = (job.get("title") or "").strip()
        if not title:
            continue
        titles.append(title)
        loc = job.get("location") or {}
        if isinstance(loc, dict):
            locations.append(", ".join(part for part in [loc.get("city") or "", loc.get("country") or ""] if part))
        else:
            locations.append(str(loc))
    return _accept_sample(
        name, country, data.get("name") or "", titles, locations, "workable",
        f"https://apply.workable.com/{token}/", client, renderer,
    )


def _smartrecruiters(client, name, country, token, renderer):
    try:
        response = _open(client, f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100")
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    posts = (response.json() or {}).get("content") or []
    titles, locations = [], []
    for post in posts:
        title = (post.get("name") or "").strip()
        if not title:
            continue
        titles.append(title)
        loc = post.get("location") or {}
        locations.append(", ".join(part for part in [loc.get("city") or "", loc.get("region") or "", loc.get("country") or ""] if part))
    return _accept_sample(
        name, country, "", titles, locations, "smartrecruiters",
        f"https://careers.smartrecruiters.com/{token}", client, renderer,
    )


def _workday_sites(text: str) -> list[str]:
    sites = []
    for line in text.splitlines():
        raw = line.split("#", 1)[0].strip()
        if not raw.lower().startswith("allow:"):
            continue
        path = raw.split(":", 1)[1].strip().strip("/")
        site = path.split("/", 1)[0]
        if not site or site.lower() in _SKIP_SITES or site in sites:
            continue
        sites.append(site)
    return sites[:4]


def _workday(client, name, country, slug, renderer):
    alnum = "".join(ch for ch in name.lower() if ch.isalnum())
    if len(slug) < 5 or slug not in alnum:
        return None
    for cluster in _WD_CLUSTERS:
        host = f"{slug}.wd{cluster}.myworkdayjobs.com"
        origin = f"https://{host}"
        try:
            robots = _open(client, origin + "/robots.txt")
        except httpx.HTTPError:
            continue
        if robots.status_code == 200:
            sites = _workday_sites(robots.text) or ["External", "Careers"]
        elif robots.status_code == 404:
            sites = ["External", "Careers"]
        else:
            continue
        for site in sites:
            page_url = f"{origin}/{site}"
            endpoint = f"{origin}/wday/cxs/{slug}/{site}/jobs"
            from app.scraper.politeness import RobotsChecker
            if not RobotsChecker(client).is_allowed(page_url):
                continue
            try:
                response = _open(client, endpoint, method="POST", body={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""})
            except httpx.HTTPError:
                continue
            if response.status_code != 200:
                continue
            try:
                payload = response.json()
            except ValueError:
                continue
            posts = payload.get("jobPostings") or []
            titles = [(post.get("title") or "").strip() for post in posts]
            titles = [title for title in titles if title]
            locations = [(post.get("locationsText") or "").strip() for post in posts]
            facet = workday_country_facet(payload, country)
            if facet:
                facet_id, here, located = facet
                decision = decide_counts(here, located)
                if not decision.accept:
                    continue
                url = workday_filter_url(page_url, facet_id) if decision.filtered else page_url
                if decision.filtered:
                    try:
                        filtered = _open(client, endpoint, method="POST", body={
                            "appliedFacets": {"locationCountry": [facet_id]},
                            "limit": 5, "offset": 0, "searchText": "",
                        })
                        filtered_posts = (filtered.json() or {}).get("jobPostings") or []
                    except (httpx.HTTPError, ValueError):
                        continue
                    titles = [(post.get("title") or "").strip() for post in filtered_posts if (post.get("title") or "").strip()]
                    if len(titles) < 2:
                        continue
            else:
                decision = decide_board(locations, country)
                if not decision.accept or decision.filtered:
                    continue
                url = page_url
            if len(titles) < 2:
                continue
            final = _confirm(client, url, titles, renderer=renderer, workday=True, filtered=decision.filtered)
            if not final:
                continue
            return _hit(name, country, "workday", final, decision, titles)
    return None


def blank_rows(path: str, countries: set[str]) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            if (row.get("careers_url") or "").strip():
                continue
            if row.get("country") not in countries:
                continue
            rows.append(row)
        return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover direct careers links for blank seed rows.")
    parser.add_argument("--csv", default=os.path.join(os.path.dirname(__file__), "..", "seed", "company_database_import.csv"))
    parser.add_argument("--country", action="append", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    renderer = None
    if args.render:
        from app.scraper.render import PlaywrightRenderer
        renderer = PlaywrightRenderer()
    rows = blank_rows(args.csv, set(args.country))
    if args.limit:
        rows = rows[:args.limit]
    print(f"blank {len(rows)}", flush=True)
    hits = []

    def one(row):
        with _client() as client:
            found = probe_json(client, row["company_name"], row["country"], renderer)
        if not found:
            return None
        found["source_type"] = row.get("source_type") or ""
        return found

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, row) for row in rows]
        for index, future in enumerate(as_completed(futures), start=1):
            found = future.result()
            if found:
                hits.append(found)
                print(f"HIT {found['country']} | {found['name']} | {found['ats']} | {found['url']}", flush=True)
            if index % 50 == 0:
                print(f"progress {index}/{len(rows)} hits {len(hits)}", flush=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(hits, handle, indent=2)
    print(f"DONE {len(hits)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
