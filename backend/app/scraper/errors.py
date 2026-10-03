"""Map a fetch failure onto a stable category.

``last_status`` stays in the short vocabulary the admin health view already
groups on. ``error_category`` and ``scraper_status`` carry the finer label.
"""
from __future__ import annotations

import httpx

from app.scraper.ssrf import SsrfBlocked


def classify_fetch_error(exc: BaseException) -> tuple[str, str, str]:
    """Return (last_status, error_category, scraper_status)."""
    if isinstance(exc, SsrfBlocked):
        return "invalid_url", exc.verdict.upper(), "INVALID_URL"
    if isinstance(exc, httpx.TimeoutException):
        return "http_error", "TIMEOUT", "TIMEOUT"
    if isinstance(exc, httpx.ConnectError):
        text = str(exc).lower()
        if any(token in text for token in ("getaddrinfo", "name or service", "nodename", "dns")):
            return "http_error", "DNS_ERROR", "REQUIRES_REVIEW"
        return "http_error", "CONNECTION_ERROR", "REQUIRES_REVIEW"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code if exc.response is not None else 0
        if code == 403:
            return "http_error", "HTTP_403", "BLOCKED"
        if code == 404:
            return "http_error", "HTTP_404", "INVALID_URL"
        if code == 429:
            return "http_error", "HTTP_429", "BLOCKED"
        label = f"HTTP_{code}" if code else "HTTP_ERROR"
        return "http_error", label, "REQUIRES_REVIEW"
    text = str(exc).lower()
    if "size cap" in text:
        return "parse_error", "RESPONSE_TOO_LARGE", "PARSER_ERROR"
    if "content type" in text:
        return "parse_error", "INVALID_HTML", "PARSER_ERROR"
    if isinstance(exc, (ValueError, UnicodeError)):
        return "parse_error", "PARSER_FAILURE", "PARSER_ERROR"
    return "parse_error", "PARSER_FAILURE", "PARSER_ERROR"


def http_status_of(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.status_code
    return None
