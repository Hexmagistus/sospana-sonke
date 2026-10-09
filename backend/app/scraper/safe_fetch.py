"""Follow redirects only after each hop has passed the SSRF check.

The vacancy scanner, the careers-URL tester, and the page hasher all call
``follow_redirects``. A public page must not send the server to loopback, a
private range, a link-local address, or the cloud metadata service.
"""
from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urljoin

from app.scraper.ssrf import assert_safe_fetch_url

REDIRECTS = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5


def _location(response) -> str | None:
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    return headers.get("location")


def _response_url(response, current: str) -> str:
    url = getattr(response, "url", None)
    return str(url) if url else current


def next_fetch_url(response_url: str, status_code: int, location: str | None) -> str | None:
    """The next absolute URL, or None when this response is the last hop.

    Raises ``SsrfBlocked`` when ``location`` is not a public http(s) URL.
    """
    if status_code not in REDIRECTS or not location:
        return None
    nxt = urljoin(response_url, location)
    assert_safe_fetch_url(nxt)
    return nxt


def follow_redirects(request_once: Callable, url: str):
    """Call ``request_once(url)`` and follow Location only when the target is safe.

    ``request_once`` must not follow redirects itself. The first URL is checked
    before any request. At most ``MAX_REDIRECTS`` hops are followed.
    """
    assert_safe_fetch_url(url)
    current = url
    for _hop in range(MAX_REDIRECTS + 1):
        response = request_once(current)
        nxt = next_fetch_url(_response_url(response, current), response.status_code, _location(response))
        if nxt is None:
            return response
        current = nxt
    raise ValueError("too many redirects")


def checked_get(client, url: str, **kwargs):
    """Synchronous GET that checks every redirect hop."""
    headers = kwargs.pop("headers", None)

    def once(current: str):
        return client.get(current, headers=headers, follow_redirects=False)

    return follow_redirects(once, url)


async def checked_get_async(client, url: str, **kwargs):
    """Async GET that checks every redirect hop."""
    headers = kwargs.pop("headers", None)

    async def once(current: str):
        return await client.get(current, headers=headers, follow_redirects=False)

    assert_safe_fetch_url(url)
    current = url
    for _hop in range(MAX_REDIRECTS + 1):
        response = await once(current)
        nxt = next_fetch_url(_response_url(response, current), response.status_code, _location(response))
        if nxt is None:
            return response
        current = nxt
    raise ValueError("too many redirects")
