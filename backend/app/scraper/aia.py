"""Complete a server's certificate chain the way browsers do (AIA fetching).

Some careers sites send only their own certificate and leave out the
intermediate CA ("unable to get local issuer certificate"). Browsers quietly
download the missing intermediate from the URL named in the certificate's
Authority Information Access field; Python does not.

This module does that one step, for one host, on request:

* the leaf certificate is read without trusting it, only to find the AIA URL;
* the intermediate is downloaded (SSRF-checked, size-capped, short timeout);
* it is added to a fresh context built on certifi's root bundle.

Verification is NOT relaxed. The intermediate is only chain-building
material: VERIFY_X509_PARTIAL_CHAIN is switched off, so the chain must still
end at a root in certifi's bundle, the intermediate must be signed by it, and
the host name is still checked. If any step fails we return None and the
caller records the SSL_INCOMPLETE_CHAIN reason instead.
"""
from __future__ import annotations

import logging
import os
import ssl
import tempfile
import threading
import time
from urllib.parse import urlparse

import certifi
import httpx

from app.scraper.ssrf import assert_safe_fetch_url

logger = logging.getLogger(__name__)

_MAX_CERT_BYTES = 64_000
_CACHE_TTL_SECONDS = 24 * 3600.0
_CACHE_MAX = 128
_MAX_CHAIN_DEPTH = 3
_cache: dict[str, tuple[float, str | None]] = {}   # host -> (fetched_at, intermediate PEM or None)
_lock = threading.Lock()


def incomplete_chain_target(exc: BaseException) -> tuple[str, int] | None:
    """(host, port) when exc is the missing-intermediate certificate error."""
    if not isinstance(exc, httpx.ConnectError):
        return None
    if "unable to get local issuer certificate" not in str(exc).lower():
        return None
    try:
        url = exc.request.url
    except RuntimeError:
        return None
    if url.scheme != "https" or not url.host:
        return None
    return url.host, url.port or 443


def strict_context(extra_pem: str | None = None) -> ssl.SSLContext:
    """certifi roots (+ optional intermediates), host-name check on, no partial chains."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    if hasattr(ssl, "VERIFY_X509_PARTIAL_CHAIN"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
    if extra_pem:
        ctx.load_verify_locations(cadata=extra_pem)
    return ctx


def _decode(pem: str) -> dict:
    decode = getattr(getattr(ssl, "_ssl", None), "_test_decode_cert", None)
    if decode is None:
        return {}
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(pem)
        return decode(path)
    except Exception:  # unparsable certificate
        return {}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _ca_issuer_urls(pem: str) -> list[str]:
    info = _decode(pem)
    if info and info.get("subject") == info.get("issuer"):
        return []                     # self-signed: top of the chain
    return [u for u in (info.get("caIssuers") or ()) if urlparse(u).scheme in ("http", "https")]


def _download_intermediate(url: str, timeout: float) -> str | None:
    assert_safe_fetch_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        resp = client.get(url)
    if resp.status_code != 200 or len(resp.content) > _MAX_CERT_BYTES:
        return None
    body = resp.content
    if body.lstrip().startswith(b"-----BEGIN CERTIFICATE-----"):
        pem = body.decode("ascii", "ignore")
    else:
        pem = ssl.DER_cert_to_PEM_cert(body)
    try:
        strict_context(pem)          # proves it parses as a certificate
    except (ssl.SSLError, ValueError):
        return None                  # e.g. a PKCS#7 bundle; not handled
    return pem


def context_for(host: str, port: int = 443, timeout: float = 4.0) -> ssl.SSLContext | None:
    """A verifying context that also knows this host's missing intermediate, or None."""
    now = time.monotonic()
    with _lock:
        hit = _cache.get(host)
    if hit is not None and now - hit[0] < _CACHE_TTL_SECONDS:
        return strict_context(hit[1]) if hit[1] else None
    pem: str | None = None
    try:
        assert_safe_fetch_url(f"https://{host}:{port}/")
        leaf = ssl.get_server_certificate((host, port), timeout=timeout)
        # Follow the AIA links up to three levels (an intermediate can itself
        # be cross-signed by an older root that certifi has).
        found: list[str] = []
        current = leaf
        for _level in range(_MAX_CHAIN_DEPTH):
            nxt = None
            for url in _ca_issuer_urls(current)[:2]:
                nxt = _download_intermediate(url, timeout)
                if nxt:
                    break
            if not nxt or nxt in found:
                break
            found.append(nxt)
            current = nxt
        pem = "".join(found) or None
    except Exception as exc:  # network, SSRF refusal, odd certificate
        logger.debug("AIA lookup failed for %s: %s", host, exc)
        pem = None
    with _lock:
        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[host] = (now, pem)
    return strict_context(pem) if pem else None
