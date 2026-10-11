"""Check one careers URL offline. Not used by the scan cron.

    python scripts/verify_seed_careers.py --url https://careers.example.com/jobs
    python scripts/verify_seed_careers.py --url https://careers.example.com/jobs --render

``--render`` launches Playwright only for a JavaScript shell, after robots.txt
and the SSRF check have allowed the final URL. A bot-challenge page is refused
instead of rendered.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from app.core.config import settings
from app.services.seed_page import fetch_seed_page, visible_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline careers-page check.")
    parser.add_argument("--url", required=True)
    parser.add_argument(
        "--render",
        action="store_true",
        help="render a JavaScript shell with Playwright after robots and SSRF allow it",
    )
    args = parser.parse_args()
    renderer = None
    if args.render:
        from app.scraper.render import PlaywrightRenderer
        renderer = PlaywrightRenderer()
    with httpx.Client(
        timeout=settings.URL_TEST_TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": settings.URL_TEST_USER_AGENT},
    ) as client:
        page = fetch_seed_page(args.url, client, renderer=renderer)
    text = visible_text(page.html)
    print(f"ok={page.ok} status={page.status_code} rendered={page.rendered} robots={page.robots_allowed}")
    print(f"final={page.final_url or ''}")
    if page.error:
        print(f"error={page.error}")
    print(text[:500])
    return 0 if page.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
