"""Listing-URL canonicalisation that does not rewrite application links.

``canonical_listing_url`` drops tracking parameters, fragments, and a trailing
slash so the same advert is one row. ``safe_application_url`` only rejects a
non-http(s) scheme. Query strings and fragments on an application link are
kept: some employers put the job id in the query, and some single-page
portals put the route in the fragment. Stripping either can make Apply fail.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "mc_cid", "mc_eid",
    "igshid", "yclid", "_ga", "_gl", "ref", "ref_src", "trk",
}


def safe_application_url(url: str | None) -> str | None:
    if not url:
        return None
    text = url.strip()
    parsed = urlparse(text)
    if parsed.scheme.lower() not in ("http", "https"):
        return None
    if not parsed.netloc:
        return None
    return text


def canonical_listing_url(url: str | None) -> str | None:
    if not url:
        return None
    text = url.strip()
    parsed = urlparse(text)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return None
    kept = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        low = key.lower()
        if low.startswith(_TRACKING_PREFIXES) or low in _TRACKING_KEYS:
            continue
        kept.append((key, value))
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        "",
        urlencode(kept, doseq=True),
        "",
    ))


def source_domain(url: str | None) -> str | None:
    if not url:
        return None
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host or None
