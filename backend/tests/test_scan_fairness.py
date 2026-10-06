"""The cron scan's fair queue, back-off, claims and concurrency bound.

Worker threads in these tests never touch the database (the same rule the
real batch follows), so they are safe on the SQLite test database.
"""
import ssl
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.scraper import aia
from app.scraper.errors import NEEDS_REVIEW_AFTER, classify_fetch_error
from app.services import scan_batch
from app.services.scan_batch import HostGate, run_scan_batch
from app.services.scan_runner import (
    BACKOFF_CAP_HOURS, backoff_hours, claim_source, due_after_hours, release_claim, select_due,
)
from app.services.scan_service import FetchOutcome, apply_fetch

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def _company(db, name, host=None, country="South Africa", last=None, fails=0):
    url = f"https://{host or name.lower()}.example.org/careers"
    c = Company(company_name=name, careers_url=url, country=country, active=True)
    db.add(c); db.commit(); db.refresh(c)
    if last is not None or fails:
        db.add(VacancySource(company_id=c.id, url=url, ats_type="static_html",
                             last_checked=last, consecutive_failures=fails))
        db.commit()
    return c


def _ok(snapshot, client, now=None):
    return FetchOutcome(kind="ok", started=time.monotonic(), now=now,
                        ats_type="static_html", parser_used="static_html", raw_list=[])


class _NoClient:
    def __init__(self, verify=None, read_timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _run(db, **kw):
    kw.setdefault("client_factory", _NoClient)
    kw.setdefault("now", NOW)
    return run_scan_batch(db, **kw)


# ---- back-off --------------------------------------------------------------

def test_permanent_failures_back_off_to_a_week_and_transient_ones_cap_at_three_days():
    assert [backoff_hours(n, "HTTP_404") for n in (1, 2, 3, 9)] == [24, 72, BACKOFF_CAP_HOURS,
                                                                    BACKOFF_CAP_HOURS]
    assert backoff_hours(1, "DNS_ERROR") == 24
    assert backoff_hours(3, "SSL_INCOMPLETE_CHAIN") == BACKOFF_CAP_HOURS
    assert backoff_hours(1, "TIMEOUT") == 6
    assert backoff_hours(5, "TIMEOUT") == 32
    assert backoff_hours(9, "TIMEOUT") == 72          # still tried twice a week
    assert backoff_hours(9) == BACKOFF_CAP_HOURS       # rows without a category: unchanged


def test_status_answers_are_not_asked_again_every_six_hours():
    url = "https://example.org/careers"
    assert due_after_hours(url, 0, 0, None, "robots_disallowed") == 168
    assert due_after_hours(url, 0, 0, None, "javascript_required") == 168
    assert due_after_hours(url, 0, 0, None, "blocked") == 72
    assert due_after_hours(url, 0, 0, None, "ok") == 6


def test_backed_off_source_is_not_selected_until_its_gap_has_passed(db):
    dead = _company(db, "Dead", last=NOW - timedelta(hours=30), fails=2)
    src = db.query(VacancySource).filter_by(company_id=dead.id).one()
    src.error_category = "HTTP_404"
    db.commit()
    assert [i.company_id for i in select_due(db, 10, NOW)] == []          # 72 h gap
    assert [i.company_id for i in select_due(db, 10, NOW + timedelta(hours=43))] == [dead.id]


def _http_error(code):
    req = httpx.Request("GET", "https://gone.example.org/careers")
    return httpx.HTTPStatusError("x", request=req, response=httpx.Response(code, request=req))


def test_three_permanent_failures_mark_the_source_needs_review(db):
    c = _company(db, "Gone", last=NOW - timedelta(days=9))
    src = db.query(VacancySource).filter_by(company_id=c.id).one()
    for n in range(1, NEEDS_REVIEW_AFTER + 1):
        apply_fetch(db, src, FetchOutcome(kind="error", started=time.monotonic(), now=NOW,
                                          ats_type="static_html", exc=_http_error(404)))
        db.refresh(src)
        assert src.consecutive_failures == n
        assert (src.scraper_status == "NEEDS_REVIEW") is (n >= NEEDS_REVIEW_AFTER)
    assert src.error_category == "HTTP_404"


def test_transient_failures_never_mark_needs_review(db):
    c = _company(db, "Flaky", last=NOW - timedelta(days=9))
    src = db.query(VacancySource).filter_by(company_id=c.id).one()
    exc = httpx.ReadTimeout("timed out", request=httpx.Request("GET", src.url))
    for _ in range(5):
        apply_fetch(db, src, FetchOutcome(kind="error", started=time.monotonic(), now=NOW,
                                          ats_type="static_html", exc=exc))
    db.refresh(src)
    assert src.consecutive_failures == 5 and src.scraper_status != "NEEDS_REVIEW"


# ---- certificates ------------------------------------------------------------

def _ssl_error(reason):
    return httpx.ConnectError(f"[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                              f"{reason} (_ssl.c:1006)",
                              request=httpx.Request("GET", "https://chain.example.org/jobs"))


def test_certificate_failures_are_named():
    assert classify_fetch_error(_ssl_error("unable to get local issuer certificate"))[1] == \
        "SSL_INCOMPLETE_CHAIN"
    assert classify_fetch_error(_ssl_error("certificate has expired"))[1] == "SSL_EXPIRED"
    assert classify_fetch_error(_ssl_error("self-signed certificate"))[1] == "SSL_INVALID"
    assert classify_fetch_error(httpx.ConnectError("[Errno 104] Connection reset by peer"))[1] == \
        "CONNECTION_ERROR"


def test_only_the_missing_intermediate_error_triggers_aia():
    assert aia.incomplete_chain_target(_ssl_error("unable to get local issuer certificate")) == \
        ("chain.example.org", 443)
    assert aia.incomplete_chain_target(_ssl_error("certificate has expired")) is None
    assert aia.incomplete_chain_target(ValueError("unable to get local issuer certificate")) is None


def test_aia_context_keeps_verification_strict():
    ctx = aia.strict_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True
    assert not ctx.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN


def test_incomplete_chain_is_retried_once_with_the_aia_context(db):
    _company(db, "Chain")
    calls = []

    def fetch(snapshot, client, now=None):
        calls.append(client.verify)
        if client.verify is None:
            return FetchOutcome(kind="error", started=time.monotonic(), now=now,
                                exc=_ssl_error("unable to get local issuer certificate"))
        return _ok(snapshot, client, now)

    class Client(_NoClient):
        def __init__(self, verify=None, read_timeout=None):
            self.verify = verify

    out = _run(db, fetch_fn=fetch, client_factory=Client, aia_fn=lambda h, p: "ctx")
    assert calls == [None, "ctx"]
    assert out["companies_scanned"] == 1 and out["sources_failed"] == 0


# ---- claims: no repeat scans ------------------------------------------------

def test_a_source_claimed_by_an_overlapping_run_is_skipped(db, monkeypatch):
    old = NOW - timedelta(days=3)
    a = _company(db, "Alpha", last=old)
    b = _company(db, "Beta", last=old)
    c = _company(db, "Gamma")                       # no source row yet
    stale_queue = select_due(db, 10, NOW)           # what this run read...
    assert {i.company_id for i in stale_queue} == {a.id, b.id, c.id}
    other = select_due(db, 10, NOW)
    # ...then the other cron call claimed Alpha first.
    alpha = next(i for i in other if i.company_id == a.id)
    assert claim_source(db, alpha.source_id, alpha.claim_token, NOW + timedelta(seconds=1))

    monkeypatch.setattr(scan_batch, "select_due", lambda *_a, **_k: list(stale_queue))
    fetched = []

    def fetch(snapshot, client, now=None):
        fetched.append(snapshot.url)
        return _ok(snapshot, client, now)

    out = _run(db, fetch_fn=fetch)
    assert sorted(fetched) == sorted([b.careers_url, c.careers_url])
    assert out["skipped_already_claimed"] == 1 and out["companies_scanned"] == 2


def test_claim_is_compare_and_set(db):
    c = _company(db, "Once", last=NOW - timedelta(days=2))
    item = select_due(db, 10, NOW)[0]
    assert claim_source(db, item.source_id, item.claim_token, NOW) is True
    assert claim_source(db, item.source_id, item.claim_token, NOW) is False
    release_claim(db, item.source_id, NOW, item.claim_token)
    assert [i.company_id for i in select_due(db, 10, NOW)] == [c.id]


def test_rotation_reaches_every_source_once_before_repeating_any(db):
    """60 sources in four regions, 10 per run, a run every 15 minutes."""
    countries = ["South Africa", "Botswana", "Kenya", "Germany"]
    ids = [_company(db, f"Co{i}", country=countries[i % 4]).id for i in range(60)]
    for i in range(0, 60, 3):          # a third were scanned a few days ago
        db.add(VacancySource(company_id=ids[i], url=f"https://co{i}.example.org/careers",
                             ats_type="static_html",
                             last_checked=NOW - timedelta(days=2, hours=i)))
    db.commit()
    seen = Counter()

    def fetch(snapshot, client, now=None):
        seen[snapshot.url] += 1
        return _ok(snapshot, client, now)

    runs = []
    for run in range(6):
        runs.append(_run(db, limit=10, fetch_fn=fetch, now=NOW + timedelta(minutes=15 * run)))
    assert all(r["companies_scanned"] == 10 for r in runs)
    assert len(seen) == 60 and set(seen.values()) == {1}
    assert _run(db, limit=10, fetch_fn=fetch,
                now=NOW + timedelta(minutes=90))["companies_scanned"] == 0


def test_abandoned_fetches_give_their_place_back(db, monkeypatch):
    old = NOW - timedelta(days=4)
    slow = [_company(db, f"Slow{i}", last=old) for i in range(2)]
    fresh = _company(db, "NeverSeen")
    monkeypatch.setattr(scan_batch, "SUBMIT_RESERVE_SECONDS", 0.3)
    release = threading.Event()

    def hang(snapshot, client, now=None):
        release.wait(5)
        return _ok(snapshot, client, now)

    try:
        out = _run(db, fetch_fn=hang, max_seconds=0.6)
    finally:
        release.set()
    assert out["abandoned_in_flight"] == 3 and out["companies_scanned"] == 0
    assert out["stopped_early_on_time_budget"] is True
    time.sleep(0.2)
    db.expire_all()
    for c in slow:
        src = db.query(VacancySource).filter_by(company_id=c.id).one()
        assert src.last_checked.replace(tzinfo=timezone.utc) == old
    src = db.query(VacancySource).filter_by(company_id=fresh.id).one()
    assert src.last_checked is None
    assert {i.company_id for i in select_due(db, 10, NOW)} == {fresh.id, *[c.id for c in slow]}


def test_a_crashing_fetch_is_recorded_and_the_batch_continues(db):
    bad = _company(db, "Bad")
    good = _company(db, "Good")

    def fetch(snapshot, client, now=None):
        if "bad" in snapshot.url:
            raise RuntimeError("adapter bug")
        return _ok(snapshot, client, now)

    out = _run(db, fetch_fn=fetch)
    assert out["companies_scanned"] == 2 and out["sources_failed"] == 1
    db.expire_all()
    assert db.query(VacancySource).filter_by(company_id=bad.id).one().consecutive_failures == 1
    assert db.query(VacancySource).filter_by(company_id=good.id).one().last_status == "empty"


# ---- concurrency bound and politeness --------------------------------------

def _tracking_fetch(delay, per_host=False):
    state = {"now": 0, "peak": 0, "hosts": Counter(), "host_peak": 0}
    lock = threading.Lock()

    def fetch(snapshot, client, now=None):
        host = scan_batch.host_of(snapshot.url)
        with lock:
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
            state["hosts"][host] += 1
            state["host_peak"] = max(state["host_peak"], state["hosts"][host])
        time.sleep(delay)
        with lock:
            state["now"] -= 1
            state["hosts"][host] -= 1
        return _ok(snapshot, client, now)

    return fetch, state


def test_concurrency_never_exceeds_the_worker_count(db):
    for i in range(12):
        _company(db, f"Host{i}")
    fetch, state = _tracking_fetch(0.15)
    out = _run(db, fetch_fn=fetch, workers=4, max_seconds=20)
    assert out["companies_scanned"] == 12
    assert 2 <= state["peak"] <= 4


def test_process_wide_fetch_cap_holds_even_with_more_workers(db):
    for i in range(14):
        _company(db, f"Wide{i}")
    fetch, state = _tracking_fetch(0.15)
    out = _run(db, fetch_fn=fetch, workers=12, max_seconds=20)
    assert out["companies_scanned"] == 14
    assert state["peak"] <= scan_batch.MAX_CONCURRENT_FETCHES


def test_one_source_per_host_in_flight(db):
    for i in range(4):
        _company(db, f"Shared{i}", host="shared")
    for i in range(4):
        _company(db, f"Own{i}")
    fetch, state = _tracking_fetch(0.1)
    out = _run(db, fetch_fn=fetch, workers=5, max_seconds=20)
    assert out["companies_scanned"] == 8
    assert state["host_peak"] == 1
    assert state["peak"] >= 2


def test_host_gate_spaces_requests_to_the_same_host():
    clock = {"t": 100.0}
    gate = HostGate(1.0, clock=lambda: clock["t"], sleep=lambda s: None)
    assert gate.reserve("a.example", "src1") == 0
    assert gate.reserve("a.example", "src1") == 0        # robots.txt then page: one visit
    assert gate.reserve("a.example", "src2") == 1.0      # another employer on that host waits
    assert gate.reserve("a.example", "src3") == 2.0
    assert gate.reserve("b.example", "src3") == 0
    clock["t"] += 5
    assert gate.reserve("a.example", "src4") == 0
    assert gate.reserve("c.example") == 0
    assert gate.reserve("c.example") == 1.0              # unknown owner: always spaced


def test_host_gate_runs_on_real_requests():
    waits = []
    gate = HostGate(1.0, sleep=waits.append)
    transport = httpx.MockTransport(lambda r: httpx.Response(200))
    with httpx.Client(transport=transport, event_hooks={"request": [gate.before_request]}) as c:
        gate.set_owner("one")
        c.get("https://shared.example/robots.txt"); c.get("https://shared.example/jobs")
        gate.set_owner("two")
        c.get("https://shared.example/jobs")
    assert len(waits) == 1 and 0.9 < waits[0] <= 1.0


def test_scan_client_uses_short_timeouts_and_the_host_gate():
    with scan_batch.make_scan_client() as client:
        assert client.timeout.connect == scan_batch.CONNECT_TIMEOUT_SECONDS == 4.0
        assert client.timeout.read == scan_batch.READ_TIMEOUT_SECONDS == 6.0
        assert scan_batch.HOST_GATE.before_request in client.event_hooks["request"]


def test_slow_sources_get_the_longer_read_timeout_early_in_the_run(db, monkeypatch):
    slow = _company(db, "Slow", last=NOW - timedelta(days=2))
    src = db.query(VacancySource).filter_by(company_id=slow.id).one()
    src.response_time_ms = 7200
    db.commit()
    timed_out = _company(db, "TimedOut", last=NOW - timedelta(days=2), fails=1)
    src = db.query(VacancySource).filter_by(company_id=timed_out.id).one()
    src.error_category = "TIMEOUT"
    src.last_checked = NOW - timedelta(days=3)
    db.commit()
    quick = _company(db, "Quick")
    dead = _company(db, "DeadSlow", last=NOW - timedelta(days=5), fails=2)
    db.query(VacancySource).filter_by(company_id=dead.id).update(
        {VacancySource.error_category: "TIMEOUT", VacancySource.response_time_ms: 11000})
    db.commit()
    items = {i.company_id: i.slow for i in select_due(db, 10, NOW)}
    # Two timeouts in a row: probably dead, back to the normal timeout.
    assert items == {slow.id: True, timed_out.id: True, quick.id: False, dead.id: False}
    db.query(VacancySource).filter_by(company_id=dead.id).update({VacancySource.active: False})
    db.commit()

    used = {}

    class Client(_NoClient):
        def __init__(self, verify=None, read_timeout=None):
            self.read_timeout = read_timeout

    def fetch(snapshot, client, now=None):
        used[snapshot.url] = client.read_timeout
        return _ok(snapshot, client, now)

    out = _run(db, fetch_fn=fetch, client_factory=Client)
    assert out["companies_scanned"] == 3
    assert used[slow.careers_url] == used[timed_out.careers_url] == \
        scan_batch.SLOW_READ_TIMEOUT_SECONDS
    assert used[quick.careers_url] is None

    # Too little time left for a slow source: it is not started (and keeps its place).
    db.query(VacancySource).update({VacancySource.last_checked: NOW - timedelta(days=5)})
    for c in (slow, timed_out):     # the quick fake fetch above reset their timings
        db.query(VacancySource).filter_by(company_id=c.id).update(
            {VacancySource.response_time_ms: 7200})
    db.commit()
    used.clear()
    out = _run(db, fetch_fn=fetch, client_factory=Client,
               max_seconds=scan_batch.SLOW_SUBMIT_RESERVE_SECONDS - 1)
    assert list(used) == [quick.careers_url]
    assert out["stopped_early_on_time_budget"] is True


def test_cron_default_budget_returns_well_before_the_30s_timeout():
    import inspect
    from app.scheduler.jobs import scan_due_companies
    sig = inspect.signature(scan_due_companies)
    budget = sig.parameters["max_seconds"].default
    assert budget + scan_batch.APPLY_GRACE_SECONDS < 30
