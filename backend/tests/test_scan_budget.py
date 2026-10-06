"""The cron scan returns inside its time budget, wrap-up included.

On Oct 6 a run with a 22 s budget answered 25.6 s after it started: in-flight
fetches and late writes ran past the budget. Now every request of an
in-flight fetch is cut off at the fetch deadline whatever its own timeout
(robots.txt 5 s, slow-lane read 10 s), late results are un-claimed instead of
written, and the whole call (selection, fetches, writes, release) fits in
``max_seconds``. These tests use a real local server that never answers.
"""
import functools
import inspect
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.services import scan_batch
from app.services.scan_batch import FetchBudget, make_scan_client, run_scan_batch

ROBOTS_TIMEOUT_SECONDS = 5.0   # RobotsChecker's own per-request timeout (scraper/politeness.py)


def test_default_budget_accounts_for_in_flight_fetch_timeouts():
    from app.scheduler.jobs import scan_due_companies
    budget = inspect.signature(scan_due_companies).parameters["max_seconds"].default
    assert budget <= 19                       # leaves >= 3 s for the JobRun write and the response
    # A fetch started at the last allowed moment could, by its own timeouts,
    # run robots.txt + connect + a slow-lane read: far past the end.
    worst_uncapped = ROBOTS_TIMEOUT_SECONDS + scan_batch.CONNECT_TIMEOUT_SECONDS \
        + scan_batch.SLOW_READ_TIMEOUT_SECONDS
    assert worst_uncapped > scan_batch.SUBMIT_RESERVE_SECONDS + scan_batch.WRAPUP_RESERVE_SECONDS
    # So requests are capped at the fetch deadline, and what follows it
    # (waiting for cut-off fetches, the release commit) fits in the reserve.
    assert scan_batch.FETCH_GRACE_SECONDS + scan_batch.RELEASE_RESERVE_SECONDS \
        <= scan_batch.WRAPUP_RESERVE_SECONDS
    assert scan_batch.SUBMIT_RESERVE_SECONDS < scan_batch.SLOW_SUBMIT_RESERVE_SECONDS


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_GET(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        if host.startswith("hang"):
            time.sleep(30)                    # never answers within any test budget
            return
        body = b"<html><body><p>No vacancies right now.</p></body></html>"
        self.send_response(404 if self.path == "/robots.txt" else 200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def local_server(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    real = socket.getaddrinfo

    def fake(host, port, *a, **k):
        if isinstance(host, str) and host.endswith(".budget.test"):
            return real("127.0.0.1", port, *a, **k)
        return real(host, port, *a, **k)

    monkeypatch.setattr(socket, "getaddrinfo", fake)
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def test_a_request_never_outlives_the_fetch_deadline(local_server):
    budget = FetchBudget(time.monotonic() + 0.6)
    url = f"http://hang.budget.test:{local_server}/careers"
    scan_batch.HOST_GATE.set_owner("one-source", budget)   # what _fetch_task does
    t0 = time.monotonic()
    with make_scan_client(budget=budget, read_timeout=scan_batch.SLOW_READ_TIMEOUT_SECONDS) as c:
        with pytest.raises(httpx.TimeoutException) as err:
            c.get(url, timeout=ROBOTS_TIMEOUT_SECONDS)       # the robots.txt call's own timeout
        assert time.monotonic() - t0 < 0.6 + 0.3
        assert budget.capped
        # After the deadline a request does not even connect.
        t1 = time.monotonic()
        with pytest.raises(httpx.TimeoutException):
            c.get(url)
        assert time.monotonic() - t1 < 0.1

    scan_batch.HOST_GATE.set_owner(None)

    class Outcome:
        exc = err.value
    assert budget.cut_short(Outcome())


def test_host_gate_wait_does_not_cross_the_deadline():
    gate = scan_batch.HostGate(1.0, sleep=lambda s: pytest.fail("slept past the deadline"))
    budget = FetchBudget(time.monotonic() + 0.5)
    gate.set_owner("a")
    gate.reserve("shared.example", "a")
    gate.set_owner("b", budget)                  # another source must wait 1 s: more than is left
    with pytest.raises(httpx.TimeoutException):
        gate.before_request(httpx.Request("GET", "https://shared.example/jobs"))
    assert budget.capped


def test_budget_does_not_touch_requests_that_have_time(local_server):
    budget = FetchBudget(time.monotonic() + 30)
    with make_scan_client(budget=budget) as c:
        r = c.get(f"http://ok.budget.test:{local_server}/careers")
    assert r.status_code == 200 and budget.capped is False


def _scaled_budget(monkeypatch):
    """The production timeline, shrunk so a test takes about two seconds."""
    for name, value in (("WRAPUP_RESERVE_SECONDS", 0.6), ("FETCH_GRACE_SECONDS", 0.2),
                        ("RELEASE_RESERVE_SECONDS", 0.2), ("SUBMIT_RESERVE_SECONDS", 0.8),
                        ("SLOW_SUBMIT_RESERVE_SECONDS", 1.2)):
        monkeypatch.setattr(scan_batch, name, value)


def test_run_returns_within_budget_with_hanging_sites_in_flight(db, local_server, monkeypatch):
    _scaled_budget(monkeypatch)
    old = datetime.now(timezone.utc) - timedelta(days=3)
    hanging, healthy = [], []
    for i in range(4):
        url = f"http://hang{i}.budget.test:{local_server}/careers"
        c = Company(company_name=f"Hang{i}", careers_url=url, country="South Africa", active=True)
        db.add(c); db.commit()
        db.add(VacancySource(company_id=c.id, url=url, ats_type="static_html", last_checked=old))
        hanging.append(c)
    for i in range(3):
        url = f"http://ok{i}.budget.test:{local_server}/careers"
        c = Company(company_name=f"Ok{i}", careers_url=url, country="Kenya", active=True)
        db.add(c)
        healthy.append(c)
    db.commit()

    t0 = time.monotonic()
    out = run_scan_batch(db, max_seconds=2.0, workers=6)   # real fetch_source, robots.txt on
    elapsed = time.monotonic() - t0
    assert elapsed <= 2.0 + 0.25, elapsed
    assert out["cut_short_by_budget"] == 4 and out["released_unfinished"] == 4
    assert out["companies_scanned"] == 3 and out["sources_failed"] == 0
    db.expire_all()
    for c in hanging:     # cut off by the budget: not a TIMEOUT failure, place kept
        src = db.query(VacancySource).filter_by(company_id=c.id).one()
        assert src.consecutive_failures == 0 and src.error_category is None
        assert src.last_checked.replace(tzinfo=timezone.utc) == old
    for c in healthy:
        assert db.query(VacancySource).filter_by(company_id=c.id).one().last_status == "empty"


def test_late_results_are_released_not_written_past_the_budget(db, monkeypatch):
    _scaled_budget(monkeypatch)
    monkeypatch.setattr(scan_batch, "APPLY_PER_VACANCY_SECONDS", 1.0)   # "a big board"
    c = Company(company_name="Big", careers_url="https://big.example.org/jobs", active=True)
    db.add(c); db.commit()

    def fetch(snapshot, client, now=None):
        time.sleep(0.9)
        return scan_batch.FetchOutcome(kind="ok", started=time.monotonic(), now=now,
                                       raw_list=[object()] * 5)

    class NoClient:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    t0 = time.monotonic()
    out = run_scan_batch(db, max_seconds=2.0, fetch_fn=fetch, client_factory=NoClient)
    assert time.monotonic() - t0 <= 2.0 + 0.25
    assert out["companies_scanned"] == 0 and out["released_unfinished"] == 1
    db.expire_all()
    assert db.query(VacancySource).filter_by(company_id=c.id).one().last_checked is None


def test_cron_endpoint_answers_within_budget_including_wrap_up(client, db, local_server,
                                                               monkeypatch):
    """End to end: HTTP request -> run_job -> batch -> JobRun commit -> response."""
    from app.core.config import settings
    from app.scheduler import registry
    from app.scheduler.jobs import scan_due_companies
    _scaled_budget(monkeypatch)
    monkeypatch.setattr(settings, "CRON_SECRET", "s3cret")
    monkeypatch.setitem(registry.JOBS, "scan_due_companies",
                        functools.partial(scan_due_companies, max_seconds=2.0))
    for i in range(6):
        url = f"http://hang{i}.budget.test:{local_server}/careers"
        db.add(Company(company_name=f"H{i}", careers_url=url, active=True))
    db.commit()
    t0 = time.monotonic()
    r = client.post("/api/v1/cron/run/scan_due_companies", headers={"X-Cron-Secret": "s3cret"})
    elapsed = time.monotonic() - t0
    assert r.status_code == 200 and r.json()["status"] == "success"
    assert elapsed <= 2.0 + 0.5, elapsed


def test_write_estimate_learns_from_the_runs_own_writes():
    clock = scan_batch.ApplyClock()

    class P:
        def __init__(self, n):
            self.raw_list = [object()] * n
    assert clock.estimate(P(100)) == pytest.approx(
        scan_batch.APPLY_BASE_SECONDS + 100 * scan_batch.APPLY_PER_VACANCY_SECONDS)
    clock.observe(P(100), 9.0)                 # 90 ms per vacancy on a slow database
    assert clock.estimate(P(100)) >= 9.0
    clock.observe(P(10), 0.01)                 # the slowest write seen still counts
    assert clock.estimate(P(100)) >= 9.0
    clock.observe(P(0), 0.05)
    assert clock.estimate(P(0)) == pytest.approx(0.05)
