"""Find official careers landing pages for large groups and listed companies.

The page does not have to list openings. It must be HTTP 200, allowed by
robots.txt, on the employer's own domain or its own ATS tenant, and clearly
a careers or jobs page (host, path, title, or heading). The official site
comes from Wikidata. Homepage links and common paths are both tried.

    python scripts/discover_careers_landing.py --names Adidas "ASML Holding" --out /tmp/spot.jsonl

The scan cron does not call this script. ``--render`` is optional and only
used when a shell's path is not already a careers path.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.seed_landing import (
    choose_entity,
    clean_stored_url,
    extract_careers_links,
    hostname,
    landing_eligible,
    language_homes,
    needs_listing_proof,
    ordered_candidates,
    page_is_careers,
    parse_wikidata_entity,
    registrable_domain,
    url_belongs_to_employer,
)
from app.services.seed_page import fetch_seed_page, looks_like_js_shell

UA = settings.URL_TEST_USER_AGENT + " offline-careers-landing"
WIKI_API = "https://www.wikidata.org/w/api.php"
_MAX_FETCHES = 8
_wiki_lock = threading.Lock()
_next_wiki = 0.0


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": UA, "Accept": "text/html,application/json"},
        follow_redirects=False,
        timeout=httpx.Timeout(12.0, connect=4.0),
    )


def _wiki_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": UA, "Accept": "application/json"},
        follow_redirects=True,
        timeout=httpx.Timeout(20.0, connect=5.0),
    )


def _wiki_pause():
    global _next_wiki
    with _wiki_lock:
        wait = _next_wiki - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _next_wiki = time.monotonic() + 0.2


def _wiki_get(client: httpx.Client, params: dict) -> dict | None:
    _wiki_pause()
    try:
        response = client.get(WIKI_API, params=params)
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except json.JSONDecodeError:
        return None


def _search_ids(client: httpx.Client, text: str) -> list[str]:
    payload = _wiki_get(client, {
        "action": "wbsearchentities",
        "search": text,
        "language": "en",
        "type": "item",
        "limit": 5,
        "format": "json",
    })
    if not payload:
        return []
    return [row["id"] for row in payload.get("search") or [] if row.get("id")]


def _load_entities(client: httpx.Client, qids: list[str]) -> list:
    found = []
    for start in range(0, len(qids), 40):
        chunk = qids[start:start + 40]
        payload = _wiki_get(client, {
            "action": "wbgetentities",
            "ids": "|".join(chunk),
            "props": "claims|labels|descriptions",
            "languages": "en",
            "format": "json",
        })
        entities = (payload or {}).get("entities") or {}
        for qid in chunk:
            parsed = parse_wikidata_entity(qid, entities.get(qid) or {})
            if parsed is not None:
                found.append(parsed)
    return found


def resolve_official(client: httpx.Client, name: str, country: str, *, require_listing: bool):
    queries = [name]
    short = name
    for suffix in (
        " Inc.", " Inc", " PLC", " Plc", " Ltd.", " Ltd", " Limited",
        " Corporation", " Corp.", " AG", " SE", " NV", " N.V.", " S.A.",
        " SA", " Group", " Holdings",
    ):
        if short.endswith(suffix):
            short = short[: -len(suffix)].strip(" ,")
    if short and short != name:
        queries.append(short)
    seen: set[str] = set()
    for query in queries:
        ids = [qid for qid in _search_ids(client, query) if qid not in seen]
        seen.update(ids)
        if not ids:
            continue
        chosen = choose_entity(
            name, country, _load_entities(client, ids), require_listing=require_listing,
        )
        if chosen is not None:
            return chosen
    return None


def _belongs(name: str, official: str, requested: str, final: str, *, from_homepage: bool) -> bool:
    started_on_official = registrable_domain(hostname(requested)) == registrable_domain(hostname(official))
    return url_belongs_to_employer(
        name, official, final, linked_from_homepage=from_homepage or started_on_official,
    )


def _consider(client, name, official, url, *, from_homepage: bool, renderer):
    page = fetch_seed_page(url, client, renderer=None)
    final = page.final_url or url
    if page.error == "robots" or page.robots_allowed is False or not page.ok:
        return None
    if not _belongs(name, official, url, final, from_homepage=from_homepage):
        return None
    if page_is_careers(final, page.html or ""):
        return final
    if renderer is not None and looks_like_js_shell(page.html or ""):
        rendered = fetch_seed_page(final, client, renderer=renderer)
        rendered_url = rendered.final_url or final
        if rendered.ok and _belongs(name, official, url, rendered_url, from_homepage=from_homepage):
            if page_is_careers(rendered_url, rendered.html or ""):
                return rendered_url
    return None


def probe_landing(client, name: str, country: str, official: str, *, renderer) -> str | None:
    home = fetch_seed_page(official, client, renderer=None)
    links: list[str] = []
    prefixes: list[str] = []
    base = official
    if home.ok and home.html:
        base = home.final_url or official
        links = extract_careers_links(home.html, base)
        prefixes = [urlparse_path(item) for item in language_homes(home.html, base)]
    homepage_set = set(links)
    origin = base if home.ok else official
    candidates = ordered_candidates(name, country, origin, links, prefixes)
    if not candidates:
        candidates = ordered_candidates(name, country, official, links, prefixes)
    for url in candidates[:_MAX_FETCHES]:
        found = _consider(
            client, name, official, url,
            from_homepage=url in homepage_set, renderer=renderer,
        )
        if found:
            return clean_stored_url(found)
    return None


def urlparse_path(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).path or ""


def _selected(path: str, names: set[str] | None, countries: set[str] | None, skip: set[str]) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("careers_url") or "").strip():
                continue
            name = row.get("company_name") or ""
            if name in skip:
                continue
            if names is not None and name not in names:
                continue
            country = row.get("country") or ""
            if countries is not None and country not in countries:
                continue
            note = row.get("relevance_note") or ""
            kind = row.get("source_type") or ""
            eligible = landing_eligible(kind, note)
            proof = needs_listing_proof(kind, note, country)
            if not eligible and not proof:
                continue
            rows.append({
                "name": name,
                "country": country,
                "source_type": kind,
                "note": note,
                "require_listing": proof and not eligible,
            })
    return rows


def _one(row: dict, renderer) -> dict | None:
    wiki = _wiki_client()
    web = _client()
    try:
        official = resolve_official(
            wiki, row["name"], row["country"], require_listing=row["require_listing"],
        )
        if official is None:
            return None
        url = probe_landing(web, row["name"], row["country"], official.website, renderer=renderer)
        if not url:
            return {
                "name": row["name"], "country": row["country"], "source_type": row["source_type"],
                "official": official.website, "qid": official.qid, "url": "", "scope": "",
            }
        return {
            "name": row["name"],
            "country": row["country"],
            "source_type": row["source_type"],
            "official": official.website,
            "qid": official.qid,
            "url": url,
            "scope": "global",
            "note": row["note"],
        }
    except Exception as exc:
        return {
            "name": row["name"], "country": row["country"], "source_type": row["source_type"],
            "url": "", "error": type(exc).__name__,
        }
    finally:
        wiki.close()
        web.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=os.path.join(os.path.dirname(__file__), "..", "seed", "company_database_import.csv"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--names", nargs="*")
    parser.add_argument("--country", action="append", default=[])
    parser.add_argument("--skip", nargs="*", default=["Liveperson Inc.", "NICE Ltd."])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    names = set(args.names) if args.names else None
    countries = set(args.country) if args.country else None
    rows = _selected(args.csv, names, countries, set(args.skip))
    if args.limit:
        rows = rows[: args.limit]
    done: set[tuple[str, str]] = set()
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as handle:
            for line in handle:
                try:
                    saved = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done.add((saved.get("name") or "", saved.get("country") or ""))
        rows = [row for row in rows if (row["name"], row["country"]) not in done]
    renderer = None
    if args.render:
        from app.scraper.render import PlaywrightRenderer

        class _LockedRenderer:
            def __init__(self, inner):
                self._inner = inner
                self._lock = threading.Lock()

            def render(self, url: str) -> str:
                with self._lock:
                    return self._inner.render(url)

        renderer = _LockedRenderer(PlaywrightRenderer())
    print(f"rows {len(rows)} resume {len(done)}", flush=True)
    lock = threading.Lock()
    hits = 0
    with open(args.out, "a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = [pool.submit(_one, row, renderer) for row in rows]
            for future in as_completed(futures):
                result = future.result()
                if not result:
                    continue
                with lock:
                    handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                    handle.flush()
                    if result.get("url"):
                        hits += 1
                        print(f"HIT {result['country']} {result['name']} {result['url']}", flush=True)
    print(f"done hits {hits}", flush=True)


if __name__ == "__main__":
    main()
