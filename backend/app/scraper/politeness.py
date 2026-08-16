"""Politeness controls (blueprint section 22): robots.txt + rate limiting + backoff.

The scraper reads only publicly-listed vacancies and must be a good citizen:
respect robots.txt, space out requests per domain, and back off on errors. This
module is used by the deployed scanner; in tests the HTTP client is injected so
robots handling can be exercised offline.
"""
from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings


class RobotsChecker:
    def __init__(self, client: httpx.Client, user_agent: str | None = None) -> None:
        self._client = client
        self._ua = user_agent or settings.URL_TEST_USER_AGENT
        self._cache: dict[str, RobotFileParser | None] = {}

    def _rules_for(self, url: str) -> RobotFileParser | None:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in self._cache:
            return self._cache[base]
        rp = RobotFileParser()
        try:
            resp = self._client.get(f"{base}/robots.txt", timeout=10.0)
            if resp.status_code >= 400:
                rp = None  # no robots.txt -> allowed
            else:
                rp.parse(resp.text.splitlines())
        except Exception:
            rp = None  # unreachable robots -> treat as allowed but caller may log
        self._cache[base] = rp
        return rp

    def is_allowed(self, url: str) -> bool:
        rp = self._rules_for(url)
        return True if rp is None else rp.can_fetch(self._ua, url)


class RateLimiter:
    """Simple per-domain minimum-interval limiter."""

    def __init__(self, min_interval_seconds: float = 2.0) -> None:
        self._min = min_interval_seconds
        self._last: dict[str, float] = {}

    def wait(self, url: str, sleep=time.sleep) -> None:
        domain = urlparse(url).netloc
        now = time.monotonic()
        last = self._last.get(domain)
        if last is not None:
            elapsed = now - last
            if elapsed < self._min:
                sleep(self._min - elapsed)
        self._last[domain] = time.monotonic()


def request_with_backoff(client: httpx.Client, url: str, retries: int = 3,
                         base_delay: float = 0.5, sleep=time.sleep) -> httpx.Response:
    """GET with exponential backoff on transient (5xx / network) errors."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client.get(url)
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
            return resp
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < retries - 1:
                sleep(base_delay * (2 ** attempt))
    assert last_exc is not None
    raise last_exc
