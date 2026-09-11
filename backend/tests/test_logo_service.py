"""Tests for company icon discovery (network mocked, mirrors test_url_tester.py)."""
import asyncio

import httpx

from app.services.logo_service import discover_favicon


def _run(coro):
    return asyncio.run(coro)


def test_prefers_apple_touch_icon_over_bare_favicon():
    html = (
        "<html><head>"
        '<link rel="icon" href="/favicon.ico">'
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
        "</head></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await discover_favicon("https://acme.example.com/", None, client=client)

    assert _run(go()) == "https://acme.example.com/apple-touch-icon.png"


def test_relative_icon_href_resolved_absolute():
    html = '<html><head><link rel="shortcut icon" href="assets/icon-32.png"></head></html>'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await discover_favicon("https://acme.example.com/about", None, client=client)

    assert _run(go()) == "https://acme.example.com/assets/icon-32.png"


def test_falls_back_to_default_favicon_ico_location():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD":
            return httpx.Response(200, request=request)
        return httpx.Response(200, text="<html><head></head></html>", request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await discover_favicon("https://acme.example.com/", None, client=client)

    assert _run(go()) == "https://acme.example.com/favicon.ico"


def test_no_icon_and_no_default_favicon_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD":
            return httpx.Response(404, request=request)
        return httpx.Response(200, text="<html><head></head></html>", request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await discover_favicon("https://acme.example.com/", None, client=client)

    assert _run(go()) is None


def test_fetch_failure_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await discover_favicon("https://down.example.com/", None, client=client)

    assert _run(go()) is None


def test_no_website_and_ats_careers_url_never_fetched():
    # An ATS-hosted careers URL must never be treated as the employer's own page —
    # if that's all we have, there's nothing to fetch at all.
    assert _run(discover_favicon(None, "https://acme.myworkdayjobs.com/careers")) is None


def test_no_urls_at_all_returns_none_without_network():
    assert _run(discover_favicon(None, None)) is None
