"""Tests for the URL tester (network mocked so tests are deterministic and offline)."""
import asyncio

import httpx

from app.services.url_tester import looks_like_careers, test_url as check_url, status_from_result


def test_looks_like_careers_heuristic():
    assert looks_like_careers("https://careers.goldfields.com/")
    assert looks_like_careers("https://x.co.za/", "<title>Job opportunities</title>")
    assert looks_like_careers("https://x.co.za/recruitment")
    assert not looks_like_careers("https://x.co.za/about-us", "<title>About</title>")


def test_test_url_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<title>Careers</title>", request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await check_url("https://careers.example.com/", client=client)

    import asyncio
    result = asyncio.run(go())
    assert result.ok is True
    assert result.status_code == 200
    assert result.looks_like_careers is True
    assert status_from_result(result) == "ok"


def test_test_url_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found", request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await check_url("https://example.com/careers/", client=client)

    import asyncio
    result = asyncio.run(go())
    assert result.ok is False
    assert result.status_code == 404
    # URL still contains 'careers' so heuristic is true, but status maps to needs_real_url
    assert status_from_result(result) == "needs_real_url"


def test_test_url_no_url():
    import asyncio
    result = asyncio.run(check_url(None))
    assert result.ok is False and result.error == "no_url"
    assert status_from_result(result) == "no_url"


def test_test_url_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(handler)

    async def go():
        async with httpx.AsyncClient(transport=transport) as client:
            return await check_url("https://down.example.com/careers", client=client)

    import asyncio
    result = asyncio.run(go())
    assert result.ok is False and result.error and "ConnectError" in result.error
    assert status_from_result(result) == "needs_real_url"
