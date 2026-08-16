"""Careers-URL tester (blueprint sections 13 & 21).

Validates that a stored careers URL still resolves and looks like a careers page.
Runs on import and on schedule so the platform verifies all links itself, rather
than trusting the seed data. Network fetching happens inside the deployed service
using httpx; the pure heuristic is separated out so it is testable without network.
"""
from __future__ import annotations

import re

import httpx

from app.core.config import settings
from app.schemas.company import UrlTestResult

_CAREERS_HINTS = ("career", "job", "vacan", "recruit", "opportunit", "employment", "join-us", "join us")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def looks_like_careers(url: str, html: str = "") -> bool:
    """Heuristic: does this URL/page look like a careers or vacancies page?"""
    haystack = url.lower()
    m = _TITLE_RE.search(html or "")
    if m:
        haystack += " " + m.group(1).lower()
    return any(hint in haystack for hint in _CAREERS_HINTS)


async def test_url(url: str | None, client: httpx.AsyncClient | None = None) -> UrlTestResult:
    """Fetch a URL and report whether it resolves and looks like a careers page."""
    if not url:
        return UrlTestResult(url="", ok=False, status_code=None, final_url=None,
                             looks_like_careers=False, error="no_url")

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            timeout=settings.URL_TEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": settings.URL_TEST_USER_AGENT},
        )
    try:
        resp = await client.get(url)
        html = resp.text if resp.status_code < 400 else ""
        final_url = str(resp.url)
        return UrlTestResult(
            url=url,
            ok=200 <= resp.status_code < 400,
            status_code=resp.status_code,
            final_url=final_url,
            looks_like_careers=looks_like_careers(final_url, html),
        )
    except Exception as exc:  # network error, DNS, SSL, timeout, etc.
        return UrlTestResult(url=url, ok=False, status_code=None, final_url=None,
                             looks_like_careers=looks_like_careers(url),
                             error=f"{type(exc).__name__}: {exc}")
    finally:
        if owns_client:
            await client.aclose()


def status_from_result(result: UrlTestResult) -> str:
    """Map a URL-test result to a company scraping_status value."""
    if result.error == "no_url":
        return "no_url"
    if result.ok and result.looks_like_careers:
        return "ok"
    if result.ok and not result.looks_like_careers:
        return "needs_review"
    return "needs_real_url"
