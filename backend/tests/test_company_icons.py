"""Fetch-once icon storage: polite, size/type-checked, served from our own DB."""
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.scheduler.jobs import discover_company_icons
from app.scheduler.registry import DEFAULT_SCHEDULE, JOBS
from app.scraper.politeness import RateLimiter, RobotsChecker
from app.services.logo_service import MAX_ICON_BYTES, fetch_company_icon, sniff_image_mime

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
ICO = b"\x00\x00\x01\x00" + b"\x00" * 32


class _NoWait(RateLimiter):
    def wait(self, url, sleep=None):  # no real sleeping in tests
        return None


def _client(routes: dict, seen: list | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(str(request.url))
        hit = routes.get(str(request.url))
        if hit is None:
            return httpx.Response(404, request=request)
        if isinstance(hit, httpx.Response):
            return hit
        body, ctype = hit
        return httpx.Response(200, content=body, headers={"content-type": ctype}, request=request)
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def _fetch(client, site="https://acme.example.com/", careers=None, known=None):
    return fetch_company_icon(site, careers, client, RobotsChecker(client), _NoWait(), known_icon_url=known)


def test_sniff_trusts_bytes_not_headers():
    assert sniff_image_mime(PNG) == "image/png"
    assert sniff_image_mime(ICO) == "image/x-icon"
    assert sniff_image_mime(b"<svg xmlns='http://www.w3.org/2000/svg'><script/></svg>") is None
    assert sniff_image_mime(b"<html>not an image</html>") is None


def test_fetches_apple_touch_icon_and_stores_bytes_and_mime():
    page = '<link rel="icon" href="/f.ico"><link rel="apple-touch-icon" href="/touch.png">'
    client = _client({
        "https://acme.example.com/robots.txt": (b"User-agent: *\nAllow: /", "text/plain"),
        "https://acme.example.com/": (page.encode(), "text/html"),
        "https://acme.example.com/touch.png": (PNG, "image/png"),
    })
    got = _fetch(client)
    assert got and got.mime == "image/png" and got.data == PNG
    assert got.source_url == "https://acme.example.com/touch.png"


def test_robots_disallow_means_no_request_for_the_page():
    seen: list[str] = []
    client = _client({
        "https://acme.example.com/robots.txt": (b"User-agent: *\nDisallow: /", "text/plain"),
        "https://acme.example.com/": (b"<link rel='icon' href='/f.png'>", "text/html"),
        "https://acme.example.com/f.png": (PNG, "image/png"),
    }, seen)
    assert _fetch(client) is None
    assert seen == ["https://acme.example.com/robots.txt"]


def test_rejects_svg_oversize_and_html_masquerading_as_image():
    page = '<link rel="icon" href="/a.svg"><link rel="icon" href="/big.png"><link rel="icon" href="/fake.png">'
    client = _client({
        "https://acme.example.com/": (page.encode(), "text/html"),
        "https://acme.example.com/a.svg": (b"<svg/>", "image/svg+xml"),
        "https://acme.example.com/big.png": (PNG + b"0" * (MAX_ICON_BYTES + 1), "image/png"),
        "https://acme.example.com/fake.png": (b"<html>oops</html>", "image/png"),
    })
    assert _fetch(client) is None


def test_known_icon_url_is_tried_first_and_page_not_read_when_it_works():
    seen: list[str] = []
    client = _client({"https://cdn.example.com/i.png": (PNG, "image/png")}, seen)
    got = _fetch(client, known="https://cdn.example.com/i.png")
    assert got and got.source_url == "https://cdn.example.com/i.png"
    assert "https://acme.example.com/" not in seen


def test_ats_only_careers_url_is_never_a_source():
    seen: list[str] = []
    client = _client({}, seen)
    assert fetch_company_icon(None, "https://acme.myworkdayjobs.com/x", client,
                              RobotsChecker(client), _NoWait()) is None
    assert seen == []


def test_job_registered_and_scheduled():
    assert "discover_company_icons" in JOBS and "discover_company_icons" in DEFAULT_SCHEDULE


def _mk(db, name, country="South Africa", site=None, careers=None, **kw):
    c = Company(company_name=name, country=country, official_website=site, careers_url=careers, **kw)
    db.add(c)
    db.commit()
    return c.id


def test_job_stores_icons_in_priority_order_and_stamps_monogram_only_rows(db, monkeypatch):
    now = datetime.now(timezone.utc)
    kenya = _mk(db, "Kenya Co", "Kenya", "https://ke.example.com/")
    sa = _mk(db, "SA Co", "South Africa", "https://sa.example.com/")
    zim = _mk(db, "Zim Co", "Zimbabwe", "https://zw.example.com/")
    ats_only = _mk(db, "ATS Co", "South Africa", None, "https://x.myworkdayjobs.com/c")
    done = _mk(db, "Done Co", "South Africa", "https://done.example.com/",
               favicon_data=PNG, favicon_mime="image/png", favicon_checked_at=now)
    order: list[str] = []

    def fake_fetch(site, careers, client, robots, limiter, known_icon_url=None):
        from app.services.logo_service import FetchedIcon
        order.append(site)
        if "zw." in site:
            return None
        return FetchedIcon(site + "i.png", PNG, "image/png")

    monkeypatch.setattr("app.services.logo_service.fetch_company_icon", fake_fetch)
    out = discover_company_icons(db, limit=10, max_seconds=60)
    assert order == ["https://sa.example.com/", "https://zw.example.com/", "https://ke.example.com/"]
    assert out["icons_stored"] == 2 and out["nothing_found"] == 1 and out["no_source_monogram_only"] == 1
    db.expire_all()
    assert db.get(Company, sa).favicon_data == PNG and db.get(Company, kenya).favicon_mime == "image/png"
    assert db.get(Company, zim).favicon_data is None and db.get(Company, zim).favicon_checked_at is not None
    assert db.get(Company, ats_only).favicon_checked_at is not None
    assert db.get(Company, done).favicon_checked_at is not None

    # Second run: everything was just checked, so no one is asked again.
    order.clear()
    discover_company_icons(db, limit=10, max_seconds=60)
    assert order == []


def test_job_respects_batch_limit(db, monkeypatch):
    for i in range(5):
        _mk(db, f"Co {i}", "South Africa", f"https://c{i}.example.com/")
    calls: list[str] = []

    def fake_fetch(site, *a, **k):
        calls.append(site)
        return None

    monkeypatch.setattr("app.services.logo_service.fetch_company_icon", fake_fetch)
    out = discover_company_icons(db, limit=2, max_seconds=60)
    assert len(calls) == 2 and out["nothing_found"] == 2


def test_missed_company_is_retried_only_after_thirty_days(db, monkeypatch):
    old = datetime.now(timezone.utc) - timedelta(days=31)
    _mk(db, "Old Miss", "South Africa", "https://old.example.com/", favicon_checked_at=old)
    calls: list[str] = []
    monkeypatch.setattr("app.services.logo_service.fetch_company_icon",
                        lambda site, *a, **k: calls.append(site))
    discover_company_icons(db, limit=5, max_seconds=60)
    assert calls == ["https://old.example.com/"]


# --- route: serves from our storage, never reaches out -----------------------

def _session(db_engine):
    return sessionmaker(bind=db_engine)()


def test_route_serves_stored_bytes_with_long_cache(client, db):
    cid = _mk(db, "Stored Co", "South Africa", "https://s.example.com/",
              favicon_data=PNG, favicon_mime="image/png")
    r = client.get(f"/api/v1/companies/{cid}/icon", follow_redirects=False)
    assert r.status_code == 200 and r.content == PNG
    assert r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"] == "public, max-age=604800, stale-while-revalidate=86400"
    assert r.headers["etag"].startswith('"')
    assert r.headers["x-content-type-options"] == "nosniff"


def test_route_legacy_url_row_redirects_and_missing_is_cacheable_204(client, db):
    legacy = _mk(db, "Legacy Co", "South Africa", favicon_url="https://l.example.com/i.png")
    none = _mk(db, "None Co", "South Africa")
    r = client.get(f"/api/v1/companies/{legacy}/icon", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "https://l.example.com/i.png"
    r = client.get(f"/api/v1/companies/{none}/icon", follow_redirects=False)
    assert r.status_code == 204 and r.headers["cache-control"] == "public, max-age=86400"
