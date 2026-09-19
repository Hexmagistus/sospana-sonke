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


# --- sync twin (used by the bulk scheduler job) -------------------------------

def test_test_url_sync_ok_and_404():
    from app.services.url_tester import test_url_sync

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/dead"):
            return httpx.Response(404, text="not found", request=request)
        return httpx.Response(200, text="<title>Careers</title>", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        good = test_url_sync("https://example.com/careers", client=client)
        bad = test_url_sync("https://example.com/dead", client=client)

    assert good.ok is True and good.status_code == 200
    assert status_from_result(good) == "ok"
    assert bad.ok is False and bad.status_code == 404
    assert status_from_result(bad) == "needs_real_url"


def test_test_url_sync_no_url():
    from app.services.url_tester import test_url_sync
    result = test_url_sync("")
    assert result.ok is False and result.error == "no_url"
    assert status_from_result(result) == "no_url"


# --- bulk scheduler job -------------------------------------------------------

def test_test_all_urls_job_updates_status(db):
    """The bulk job downgrades dead links and promotes live ones, using the same
    taxonomy as the admin per-company endpoint, and stamps last_checked."""
    from app.models.company import Company
    from app.scheduler.jobs import test_all_urls

    live = Company(company_name="LiveUni", careers_url="https://live.example/careers",
                   country="Kenya", source_type="COLLEGE", active=True, scraping_status="pending")
    dead = Company(company_name="DeadUni", careers_url="https://dead.example/vacancies",
                   country="Kenya", source_type="COLLEGE", active=True, scraping_status="green_verified")
    inactive = Company(company_name="Skipped", careers_url="https://skip.example/careers",
                       country="Kenya", source_type="COLLEGE", active=False, scraping_status="pending")
    db.add_all([live, dead, inactive]); db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "dead.example":
            return httpx.Response(404, text="gone", request=request)
        return httpx.Response(200, text="<title>Job opportunities</title>", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        summary = test_all_urls(db, client=client)

    db.refresh(live); db.refresh(dead); db.refresh(inactive)
    assert summary["urls_tested"] == 2          # inactive one is not tested
    assert summary["ok"] == 1 and summary["dead"] == 1
    assert live.scraping_status == "ok"
    assert dead.scraping_status == "needs_real_url"   # 404 -> downgraded
    assert dead.last_http_status == 404
    assert live.last_checked is not None
    assert inactive.scraping_status == "pending"      # untouched


def test_test_all_urls_job_respects_time_budget(db):
    from app.models.company import Company
    from app.scheduler.jobs import test_all_urls

    for i in range(3):
        db.add(Company(company_name=f"C{i}", careers_url=f"https://c{i}.example/careers",
                       country="Ghana", source_type="COLLEGE", active=True))
    db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<title>Careers</title>", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        summary = test_all_urls(db, max_seconds=-1.0, client=client)   # budget already spent
    assert summary["stopped_early_on_time_budget"] is True
    assert summary["urls_tested"] == 0
