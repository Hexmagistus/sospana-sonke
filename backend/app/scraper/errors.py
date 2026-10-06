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
        ssl_label = ssl_error_category(text)
        if ssl_label:
            return "http_error", ssl_label, "REQUIRES_REVIEW"
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


def ssl_error_category(text: str) -> str | None:
    """Name the certificate problem instead of a generic connection error.

    SSL_INCOMPLETE_CHAIN: the server did not send its intermediate certificate
    ("unable to get local issuer certificate"); browsers fetch it themselves.
    SSL_EXPIRED: the site's certificate has expired. SSL_INVALID: any other
    verification failure (wrong host name, self-signed, ...).
    """
    low = (text or "").lower()
    if "unable to get local issuer certificate" in low:
        return "SSL_INCOMPLETE_CHAIN"
    if "certificate has expired" in low:
        return "SSL_EXPIRED"
    if "certificate verify failed" in low or "certificate_verify_failed" in low:
        return "SSL_INVALID"
    return None


# Failures that will not fix themselves between two scans: the URL is wrong,
# the host is gone or its certificate is broken. These back off faster and,
# after NEEDS_REVIEW_AFTER in a row, the source is marked NEEDS_REVIEW.
PERMANENT_CATEGORIES = frozenset({
    "HTTP_404", "HTTP_410", "DNS_ERROR", "SSL_EXPIRED", "SSL_INVALID", "SSL_INCOMPLETE_CHAIN",
    "BAD_SCHEME", "BLOCKED_HOST", "PRIVATE_IP", "DNS_PRIVATE",
})
NEEDS_REVIEW_AFTER = 3


def is_permanent(category: str | None) -> bool:
    return (category or "") in PERMANENT_CATEGORIES


def http_status_of(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.status_code
    return None
