"""http(s) links an administrator may attach to a candidate notice.

Anything else (javascript:, data:, a missing host, a URL with embedded
credentials) is refused. The stored form keeps the pasted path and query,
with only the scheme lower-cased, so the same link dedupes.
"""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def validated_notice_url(value: str | None) -> str | None:
    """Return a plain http(s) URL, or None when the field is empty."""
    if value is None:
        return None
    text = value.strip()
    if text == "":
        return None
    if any(ord(ch) < 33 or ord(ch) == 127 for ch in text):
        raise ValueError("link_url must be an http:// or https:// address")
    parsed = urlparse(text)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("link_url must start with http:// or https://")
    if parsed.username or parsed.password:
        raise ValueError("link_url must not include a username or password")
    if "\\" in text or scheme == "javascript":
        raise ValueError("link_url must start with http:// or https://")
    return urlunparse(parsed._replace(scheme=scheme))
