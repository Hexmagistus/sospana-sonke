"""Memory bounds, cheap/cacheable icon responses, and secret-free access logs."""
import inspect
import logging
from datetime import datetime, timezone

import pytest
from sqlalchemy import event

from app.core.bounded_cache import BoundedTTLCache
from app.models.company import Company
from app.services import icon_cache
from tests.conftest import register_and_login

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


# --- 1. every in-process cache is bounded ------------------------------------

class _Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_bounded_cache_caps_entries_lru_order():
    c = BoundedTTLCache(max_entries=3, max_bytes=10_000, ttl_seconds=60)
    for k in "abc":
        c.set(k, k)
    assert c.get("a") == "a"          # touch: "b" is now least recently used
    c.set("d", "d")
    assert len(c) == 3 and c.get("b") is None and c.get("a") == "a"
    assert c.evictions == 1


def test_bounded_cache_caps_bytes_and_refuses_oversize():
    c = BoundedTTLCache(max_entries=1_000, max_bytes=1_000, ttl_seconds=60, sizeof=len)
    for i in range(50):
        c.set(i, b"x" * 100)
        assert c.total_bytes <= 1_000
    assert len(c) == 10
    assert c.set("huge", b"x" * 1_001) is False and c.get("huge") is None
    assert c.total_bytes <= 1_000


def test_bounded_cache_ttl_expires_and_frees_bytes():
    clock = _Clock()
    c = BoundedTTLCache(max_entries=10, max_bytes=10_000, ttl_seconds=30, sizeof=len, clock=clock)
    c.set("k", b"abc")
    clock.t += 29
    assert c.get("k") == b"abc"
    clock.t += 1
    assert c.get("k") is None and c.total_bytes == 0 and len(c) == 0


def test_icon_caches_have_hard_limits():
    assert icon_cache.icon_bytes_cache.max_bytes <= 8 * 1024 * 1024
    assert icon_cache.icon_bytes_cache.max_entries <= 2_000
    assert icon_cache.icon_bytes_cache.ttl_seconds <= 3_600
    assert icon_cache.INDEX_MAX_ENTRIES <= 50_000
    # Filling far past the budget never exceeds it.
    for i in range(3_000):
        icon_cache.icon_bytes_cache.set(f"id{i}", icon_cache.IconBytes(b"x" * 20_000, "image/png", '"e"'))
    assert icon_cache.icon_bytes_cache.total_bytes <= icon_cache.icon_bytes_cache.max_bytes
    icon_cache.icon_bytes_cache.clear()


def test_console_outboxes_are_capped():
    from app.notifications.channels import ConsolePushProvider, ConsoleSMSProvider, OUTBOX_MAX
    from app.notifications.email import ConsoleEmailProvider
    for provider, send in ((ConsoleEmailProvider, lambda p, i: p.send(f"u{i}@example.com", "s", "b")),
                           (ConsoleSMSProvider, lambda p, i: p.send(f"082{i}", "b")),
                           (ConsolePushProvider, lambda p, i: p.send(f"tok{i}", "t", "b"))):
        provider.outbox.clear()
        p = provider()
        for i in range(450):
            send(p, i)
        assert len(provider.outbox) <= max(OUTBOX_MAX, ConsoleEmailProvider.OUTBOX_MAX)
        provider.outbox.clear()


def test_memory_helpers_never_raise():
    from app.core.memory import current_rss_mb, limit_malloc_arenas, trim_heap
    assert isinstance(limit_malloc_arenas(), bool)
    assert isinstance(trim_heap(), bool)
    rss = current_rss_mb()
    assert rss is None or rss > 0


# --- 2. icons: cheap and strongly cacheable ----------------------------------

def _mk(db, name, **kw):
    c = Company(company_name=name, country="South Africa", **kw)
    db.add(c)
    db.commit()
    return c.id


@pytest.fixture()
def count_queries(db_engine):
    seen: list[str] = []

    def _before(conn, cursor, statement, params, context, executemany):
        seen.append(statement)

    event.listen(db_engine, "before_cursor_execute", _before)
    yield seen
    event.remove(db_engine, "before_cursor_execute", _before)


def test_icon_bytes_have_etag_and_304(client, db):
    cid = _mk(db, "Stored", favicon_data=PNG, favicon_mime="image/png",
              favicon_checked_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
    r = client.get(f"/api/v1/companies/{cid}/icon")
    assert r.status_code == 200 and r.content == PNG
    etag = r.headers["etag"]
    assert "immutable" not in r.headers["cache-control"]
    r2 = client.get(f"/api/v1/companies/{cid}/icon", headers={"If-None-Match": etag})
    assert r2.status_code == 304 and r2.content == b"" and r2.headers["etag"] == etag
    r3 = client.get(f"/api/v1/companies/{cid}/icon", headers={"If-None-Match": f"W/{etag}"})
    assert r3.status_code == 304


def test_icon_with_current_version_is_immutable_for_a_year(client, db):
    checked = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    cid = _mk(db, "Versioned", favicon_data=PNG, favicon_mime="image/png", favicon_checked_at=checked)
    v = int(checked.timestamp())
    r = client.get(f"/api/v1/companies/{cid}/icon?v={v}")
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    # A stale or made-up version must not pin today's bytes under that URL.
    r = client.get(f"/api/v1/companies/{cid}/icon?v={v - 1}")
    assert "immutable" not in r.headers["cache-control"]


def test_list_exposes_icon_version_matching_the_route(client, db):
    checked = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    with_icon = _mk(db, "Has Icon", favicon_url="https://h.example.com/i.png", favicon_checked_at=checked)
    without = _mk(db, "No Icon")
    _, tokens = register_and_login(client)
    rows = client.get("/api/v1/companies?country=South%20Africa",
                      headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()
    by_id = {r["id"]: r for r in rows}
    assert by_id[with_icon]["has_icon"] is True
    assert by_id[with_icon]["icon_version"] == int(checked.timestamp())
    assert by_id[without]["has_icon"] is False and by_id[without]["icon_version"] is None
    r = client.get(f"/api/v1/companies/{with_icon}/icon?v={by_id[with_icon]['icon_version']}",
                   follow_redirects=False)
    assert r.status_code == 302 and r.headers["cache-control"] == "public, max-age=604800"


def test_unknown_company_404_is_cacheable(client, db):
    r = client.get("/api/v1/companies/00000000-0000-0000-0000-000000000000/icon")
    assert r.status_code == 404
    assert r.headers["cache-control"] == "public, max-age=3600"
    r = client.get("/api/v1/companies/" + "x" * 80 + "/icon")
    assert r.status_code == 404


def test_repeat_icon_requests_do_not_touch_the_database(client, db, count_queries):
    stored = _mk(db, "Stored", favicon_data=PNG, favicon_mime="image/png")
    legacy = _mk(db, "Legacy", favicon_url="https://l.example.com/i.png")
    none = _mk(db, "None")
    count_queries.clear()  # ignore the inserts above
    for cid in (stored, legacy, none):  # warm: one index query + one bytes query
        client.get(f"/api/v1/companies/{cid}/icon", follow_redirects=False)
    warm_queries = len(count_queries)
    assert warm_queries == 2
    for _ in range(20):
        for cid in (stored, legacy, none):
            r = client.get(f"/api/v1/companies/{cid}/icon", follow_redirects=False)
            assert r.status_code in (200, 302, 204)
    assert len(count_queries) == warm_queries  # 60 more requests, zero queries


def test_newer_version_in_the_url_rereads_just_that_company(client, db, count_queries):
    """The icon job doesn't notify this cache. The directory's ?v= (from the
    list response) is what tells the API it holds an older answer."""
    cid = _mk(db, "Later", official_website="https://later.example.com/",
              favicon_checked_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
    old_v = int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp())
    assert client.get(f"/api/v1/companies/{cid}/icon?v={old_v}").status_code == 204
    # The icon job stores bytes and re-stamps favicon_checked_at.
    checked = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    c = db.get(Company, cid)
    c.favicon_data, c.favicon_mime, c.favicon_checked_at = PNG, "image/png", checked
    db.commit()
    # Unversioned / old-version requests keep the cached answer until the index TTL.
    assert client.get(f"/api/v1/companies/{cid}/icon?v={old_v}").status_code == 204
    new_v = int(checked.timestamp())
    r = client.get(f"/api/v1/companies/{cid}/icon?v={new_v}")
    assert r.status_code == 200 and r.content == PNG
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    # Plain requests now see the fresh answer too.
    assert client.get(f"/api/v1/companies/{cid}/icon").status_code == 200


def test_made_up_versions_cannot_force_a_query_per_request(client, db, count_queries):
    cid = _mk(db, "Target", favicon_data=PNG, favicon_mime="image/png",
              favicon_checked_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
    client.get(f"/api/v1/companies/{cid}/icon")  # warm
    count_queries.clear()
    for i in range(50):
        r = client.get(f"/api/v1/companies/{cid}/icon?v={9_000_000_000 + i}")
        assert r.status_code == 200
        assert "immutable" not in r.headers["cache-control"]
    assert len(count_queries) <= 1  # one re-read per company per RECHECK_SECONDS
    for bogus in ("abc", "-1", "1e9"):
        r = client.get(f"/api/v1/companies/{cid}/icon?v={bogus}")
        assert r.status_code == 200 and "immutable" not in r.headers["cache-control"]
    assert len(count_queries) <= 1


def test_icon_bytes_cache_is_keyed_by_version(client, db):
    cid = _mk(db, "Swap", favicon_data=PNG, favicon_mime="image/png",
              favicon_checked_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
    first = client.get(f"/api/v1/companies/{cid}/icon")
    new_png = PNG + b"\x01"
    checked = datetime(2026, 10, 7, tzinfo=timezone.utc)
    c = db.get(Company, cid)
    c.favicon_data, c.favicon_checked_at = new_png, checked
    db.commit()
    r = client.get(f"/api/v1/companies/{cid}/icon?v={int(checked.timestamp())}")
    assert r.content == new_png and r.headers["etag"] != first.headers["etag"]


def test_deleted_company_icon_is_404(client, db):
    cid = _mk(db, "Gone", favicon_url="https://g.example.com/i.png",
              deleted_at=datetime.now(timezone.utc))
    assert client.get(f"/api/v1/companies/{cid}/icon", follow_redirects=False).status_code == 404


def test_icon_and_health_routes_run_on_the_event_loop():
    from app.api.routes_companies import company_icon
    from app.main import app
    health = next(r.endpoint for r in app.routes if getattr(r, "path", None) == "/health")
    assert inspect.iscoroutinefunction(health)
    assert inspect.iscoroutinefunction(company_icon)


# --- 3. access logs never contain secrets ------------------------------------

def _format_access_line(path: str, install: bool = True) -> str:
    """Emit through uvicorn's real access logger + formatter and return the line."""
    from uvicorn.logging import AccessFormatter
    from app.core.logging import configure_logging, install_uvicorn_scrubbers
    configure_logging()
    if install:
        install_uvicorn_scrubbers()
    lines: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            lines.append(self.format(record))

    handler = _Capture()
    handler.setFormatter(AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s',
                                         use_colors=False))
    access = logging.getLogger("uvicorn.access")
    old_level = access.level
    access.setLevel(logging.INFO)
    access.addHandler(handler)
    try:
        # Exactly the call uvicorn's httptools protocol makes per request.
        access.info('%s - "%s %s HTTP/%s" %d', "102.253.35.22:0", "GET", path, "1.1", 200)
    finally:
        access.removeHandler(handler)
        access.setLevel(old_level)
    assert len(lines) == 1
    return lines[0]


JWT = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwidHlwZSI6ImVtYWlsX3ZlcmlmeSJ9"
       ".p_fllNKQst4DB0rF7NQZ54wRhhlr5P03dEuv4Mf6YgI")


@pytest.mark.parametrize("path,secret", [
    (f"/api/v1/auth/verify?token={JWT}", JWT),
    ("/api/v1/notifications/digest/unsubscribe?token=abc.def.ghi", "abc.def.ghi"),
    ("/api/v1/x?page=2&api_key=SEKRET123", "SEKRET123"),
    ("/api/v1/x?reset_token=RST999&q=hi", "RST999"),
    ("/api/v1/x?code=4242", "4242"),
    ("/api/v1/x?client_secret=CS1&X-Amz-Signature=SIG1", "CS1"),
    ("/api/v1/x?X-Amz-Signature=SIG1", "SIG1"),
])
def test_access_log_scrubs_sensitive_query_values(path, secret):
    line = _format_access_line(path)
    assert secret not in line
    assert "[redacted]" in line
    assert '102.253.35.22:0 - "GET /api/v1/' in line and '200' in line


def test_scrubber_survives_uvicorns_own_logging_setup():
    """uvicorn runs logging.config.dictConfig(LOGGING_CONFIG) when it starts;
    the filter sits on the logger itself, which dictConfig doesn't remove."""
    import logging.config
    from uvicorn.config import LOGGING_CONFIG
    from app.core.logging import install_uvicorn_scrubbers
    install_uvicorn_scrubbers()
    logging.config.dictConfig(LOGGING_CONFIG)
    line = _format_access_line(f"/api/v1/auth/verify?token={JWT}", install=False)
    assert JWT not in line and "token=[redacted]" in line


def test_access_log_keeps_harmless_query_strings():
    line = _format_access_line("/api/v1/companies?country=South%20Africa&limit=100")
    assert "country=South%20Africa&limit=100" in line


def test_sentry_event_is_scrubbed_too():
    from app.core.logging import _sentry_before_send
    ev = {"request": {"url": f"https://api.example.com/api/v1/auth/verify?token={JWT}",
                      "query_string": f"token={JWT}&x=1"}}
    out = _sentry_before_send(ev, None)
    assert JWT not in str(out)
    assert out["request"]["query_string"] == "token=[redacted]&x=1"


def test_verify_flow_still_works_with_token_in_query(client):
    from app.core import security
    reg, _ = register_and_login(client)
    token = security.create_email_verification_token(reg["user"]["id"])
    r = client.get(f"/api/v1/auth/verify?token={token}")
    assert r.status_code == 200 and r.json()["status"] == "verified"
