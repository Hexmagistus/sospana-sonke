"""Politeness controls (blueprint section 22): robots.txt + rate limiting + backoff.

The scraper reads only publicly-listed vacancies and must be a good citizen:
respect robots.txt, space out requests per domain, and back off on errors. This
module is used by the deployed scanner; in tests the HTTP client is injected so
robots handling can be exercised offline.
"""
from __future__ import annotations

import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


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
        except Exception as exc:
            logger.debug("robots.txt unreachable for %s, treating as allowed: %s", base, exc)
            rp = None  # unreachable robots -> treat as allowed
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


def _retry_delay(exc: httpx.HTTPStatusError, base_delay: float, attempt: int) -> float:
    """Exponential backoff, unless a 429 names an explicit Retry-After (seconds
    or an HTTP-date) — a server that tells us how long to wait should be
    believed over a guess."""
    delay = base_delay * (2 ** attempt)
    resp = exc.response
    if resp is not None and resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        if retry_after is not None:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass  # HTTP-date form or unparsable -- fall back to the exponential delay
    return delay


def request_with_backoff(client: httpx.Client, url: str, retries: int = 3,
                         base_delay: float = 0.5, sleep=time.sleep) -> httpx.Response:
    """GET with exponential backoff on transient (5xx / 429 / network) errors.

    A 429 is a server explicitly asking us to slow down, not a permanent
    failure, so it is retried like a 5xx -- and its Retry-After header (when
    present and a plain number of seconds) sets the wait instead of guessing.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client.get(url)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError("retryable status", request=resp.request, response=resp)
            return resp
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = (_retry_delay(exc, base_delay, attempt)
                         if isinstance(exc, httpx.HTTPStatusError) else base_delay * (2 ** attempt))
                sleep(delay)
    assert last_exc is not None
    raise last_exc
