"""Reject fetches that are not public http(s) URLs.

Scraped pages are untrusted, and a careers URL is attacker-controlled data
once it is in the database. This blocks non-http schemes, loopback, private,
link-local, and cloud-metadata addresses, including when a hostname resolves
to one of those ranges.

DNS lookup is skipped when ENV=test so fixture clients stay offline. Tests
pass their own ``resolve`` callable to prove a public name that points at
127.0.0.1 is refused. Production always resolves.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import settings


class SsrfBlocked(ValueError):
    """The URL must not be fetched."""

    def __init__(self, verdict: str, url: str) -> None:
        self.verdict = verdict
        super().__init__(f"{verdict}: {url}")


_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata",
    "metadata.google.internal",
    "metadata.google",
}


def _blocked_ip(raw: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return False
    return any((
        ip.is_private,
        ip.is_loopback,
        ip.is_link_local,
        ip.is_multicast,
        ip.is_reserved,
        ip.is_unspecified,
    ))


def _default_resolve(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None)
    return [item[4][0] for item in infos]


def classify_url(url: str, resolve=None) -> str:
    """Return ``ok`` or a short refusal reason. Does not raise."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        return "bad_scheme"
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        return "blocked_host"
    if host in _BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        return "blocked_host"
    if _blocked_ip(host):
        return "private_ip"
    if resolve is None:
        if settings.ENV == "test":
            return "ok"
        resolve = _default_resolve
    try:
        addresses = resolve(host)
    except socket.gaierror:
        return "dns_error"
    except OSError:
        return "dns_error"
    if not addresses:
        return "dns_error"
    for address in addresses:
        if _blocked_ip(address):
            return "dns_private"
    return "ok"


def assert_safe_fetch_url(url: str, resolve=None) -> None:
    verdict = classify_url(url, resolve=resolve)
    if verdict != "ok":
        raise SsrfBlocked(verdict, url)
