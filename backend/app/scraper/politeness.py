"""Politeness controls (blueprint section 22): robots.txt + rate limiting + backoff.

The scraper reads only publicly-listed vacancies and must be a good citizen:
respect robots.txt, space out requests per domain, and back off on errors. This
module is used by the deployed scanner; in tests the HTTP client is injected so
robots handling can be exercised offline.
"""
from __future__ import annotations

import contextvars
import logging
import time
from contextlib import contextmanager
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings
from app.scraper.safe_fetch import REDIRECTS, follow_redirects
from app.scraper.ssrf import assert_safe_fetch_url

logger = logging.getLogger(__name__)

# A public JSON board can be large. Cap the body so one host cannot fill memory.
MAX_RESPONSE_BYTES = 5_000_000

# The cron scan sets this so one dead host cannot burn retries * timeout.
# Unset (None) leaves request_with_backoff's own `retries` argument alone.
_backoff_retry_cap: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "backoff_retry_cap", default=None,
)


@contextmanager
def backoff_retry_cap(retries: int):
    """Cap request_with_backoff attempts for the current context."""
    token = _backoff_retry_cap.set(retries)
    try:
        yield
    finally:
        _backoff_retry_cap.reset(token)


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
            robots_url = f"{base}/robots.txt"
            assert_safe_fetch_url(robots_url)
            resp = self._client.get(robots_url, timeout=5.0, follow_redirects=False)
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


def is_aws_waf_challenge(status_code: int | None, body: str) -> bool:
    """True when the host answered with an AWS WAF challenge instead of a page.

    PageUp boards (UNSW, Mater Health) sometimes do this on HTTP 202. The
    careers URL is still real; the fetch just did not receive the vacancy list.
    """
    if status_code != 202:
        return False
    low = (body or "").lower()
    return any(marker in low for marker in ("awswaf", "aws-waf", "gokuprops", "human verification"))


def request_with_backoff(client: httpx.Client, url: str, retries: int = 3,
                         base_delay: float = 0.5, sleep=time.sleep,
                         method: str = "GET", json_body: dict | None = None,
                         headers: dict | None = None,
                         form_body: dict | None = None) -> httpx.Response:
    """GET (or POST) with exponential backoff on transient (5xx / 429 / network) errors.

    A 429 is a server explicitly asking us to slow down, not a permanent
    failure, so it is retried like a 5xx -- and its Retry-After header (when
    present and a plain number of seconds) sets the wait instead of guessing.
    """
    cap = _backoff_retry_cap.get()
    if cap is not None:
        retries = max(1, min(retries, cap))
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            assert_safe_fetch_url(url)
            resp = _fetch_limited(client, url, method=method, json_body=json_body,
                                  headers=headers, form_body=form_body)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError("retryable status", request=resp.request, response=resp)
            return resp
        except ValueError:
            raise
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = (_retry_delay(exc, base_delay, attempt)
                         if isinstance(exc, httpx.HTTPStatusError) else base_delay * (2 ** attempt))
                sleep(delay)
    assert last_exc is not None
    raise last_exc


def _fetch_limited(client: httpx.Client, url: str, *, method: str,
                   json_body: dict | None, headers: dict | None = None,
                   form_body: dict | None = None) -> httpx.Response:
    """GET/POST without letting the client follow a redirect we have not checked.

    ``headers`` are sent on the request only (the client's own headers stay
    as they are). ``form_body`` posts a urlencoded form instead of JSON.
    Redirects use the same hop check as the URL tester and the page hasher.
    """
    state = {"method": method, "json": json_body, "form": form_body}

    def once(current: str):
        if state["method"].upper() == "POST":
            if state["form"] is not None:
                resp = client.post(current, data=state["form"], headers=headers,
                                   follow_redirects=False)
            else:
                resp = client.post(current, json=state["json"] or {}, headers=headers,
                                   follow_redirects=False)
        else:
            resp = client.get(current, headers=headers, follow_redirects=False)
        if resp.status_code in REDIRECTS and resp.headers.get("location"):
            state["method"] = "GET"
            state["json"] = None
            state["form"] = None
        return resp

    resp = follow_redirects(once, url)
    if resp.status_code not in REDIRECTS:
        _reject_oversized_or_binary(resp)
    return resp


def _reject_oversized_or_binary(resp: httpx.Response) -> None:
    declared = resp.headers.get("content-length")
    if declared:
        try:
            if int(declared) > MAX_RESPONSE_BYTES:
                raise ValueError("response exceeds size cap")
        except ValueError as exc:
            if "size cap" in str(exc):
                raise
    if len(resp.content) > MAX_RESPONSE_BYTES:
        raise ValueError("response exceeds size cap")
    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype.startswith(("image/", "video/", "audio/")):
        raise ValueError(f"unsupported content type {ctype}")
