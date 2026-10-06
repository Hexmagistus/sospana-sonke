"""The cron scan's batch loop: fair queue, bounded concurrency, fail fast.

Used by ``scheduler.jobs.scan_due_companies`` (called every 15 minutes by an
external cron with a 30 second request timeout).

* Who: ``scan_runner.select_due`` — never-scanned first, then the oldest
  scan, with a bounded head start for South Africa / SADC / Africa.
* No double scans: each source is claimed with a compare-and-set on its
  ``last_checked`` right before it is fetched, so two overlapping cron calls
  skip each other's sources. A source claimed but not fetched in time gets its
  old timestamp back and stays at the front of the queue.
* Throughput: up to ``workers`` (6) fetches run at once on threads (process-wide
  cap MAX_CONCURRENT_FETCHES, shared by overlapping runs, so memory stays
  bounded on the 512 MB instance). Only the network half runs on threads;
  every database write happens on the request's own session, so the batch
  needs no extra pool connections.
* Politeness: robots.txt is still checked per source; at most one source per
  host is in flight, and a request for another source on a host that was
  just used waits HOST_MIN_INTERVAL_SECONDS (see HostGate). One attempt per request (no retry loop).
* Fail fast: 4 s connect / 6 s read (10 s read for a source that was slow
  or timed out last time, started only while SLOW_SUBMIT_RESERVE_SECONDS
  remain before the fetch deadline).
* Bounded time, wrap-up included: ``max_seconds`` is the whole call, from
  choosing the batch to the last commit. Every HTTP request of every fetch is
  cut off at the fetch deadline (``max_seconds - WRAPUP_RESERVE_SECONDS``):
  its connect/read/write timeouts are shortened to the time left (see
  FetchBudget), so in-flight fetches end by then whatever their own
  timeouts. New fetches start only while SUBMIT_RESERVE_SECONDS remain. A
  result is written only if its estimated write time (ApplyClock, which
  learns from the run's own writes) still fits; anything cut
  short or left over is un-claimed in one commit and keeps its place at the
  front of the queue (it is not counted as a failure).
* Certificates: a missing intermediate is fetched once via AIA
  (``scraper.aia``) with verification left fully on; otherwise the failure is
  recorded as SSL_INCOMPLETE_CHAIN / SSL_EXPIRED / SSL_INVALID.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.vacancy import VacancySource
from app.scraper import aia
from app.scraper.politeness import backoff_retry_cap
from app.services.scan_runner import (
    DueItem, _stamp_failure, claim_source, release_claims, select_due,
)
from app.services.scan_service import (
    FetchOutcome, SourceSnapshot, apply_fetch, ensure_source, fetch_source, snapshot_of,
)

logger = logging.getLogger(__name__)

DEFAULT_WORKERS = 6
MAX_CONCURRENT_FETCHES = 6
CONNECT_TIMEOUT_SECONDS = 4.0
READ_TIMEOUT_SECONDS = 6.0
# A source that was slow (or timed out) last time gets one longer read
# timeout, so a site that needs 6-10 s to answer is still read. It is only
# started while SLOW_SUBMIT_RESERVE_SECONDS remain.
SLOW_READ_TIMEOUT_SECONDS = 10.0
# Time budget, measured back from the end of the call (max_seconds):
WRAPUP_RESERVE_SECONDS = 1.5     # fetch deadline: every request is cut off this long before the end
FETCH_GRACE_SECONDS = 0.5        # wait this long past the fetch deadline for cut-off fetches to return
RELEASE_RESERVE_SECONDS = 0.5    # the last writes (un-claiming leftovers) must start by then
SUBMIT_RESERVE_SECONDS = 5.0     # start a fetch only with this long left before the fetch deadline
SLOW_SUBMIT_RESERVE_SECONDS = 11.0
# Estimated time to write one result (apply_fetch + commit) on the remote
# database; a result whose estimate does not fit before the release reserve
# is un-claimed instead of half-written past the budget.
APPLY_BASE_SECONDS = 0.4
APPLY_PER_VACANCY_SECONDS = 0.07
AIA_MIN_SECONDS = 3.0            # only try AIA chain completion with this long left
HOST_MIN_INTERVAL_SECONDS = 1.0

_FETCH_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_FETCHES)
_CLAIM_LOCK = threading.Lock()


class HostGate:
    """Spaces requests to the same host across sources (an httpx request hook).

    Requests made for one source (robots.txt, then the page or API) go back
    to back, as a browser would. A request for a *different* source on a host
    that was just used (several employers on one ATS host) waits until
    ``interval`` has passed since that host's last request.
    """

    def __init__(self, interval: float, clock=time.monotonic, sleep=time.sleep) -> None:
        self.interval = interval
        self._last: dict[str, tuple[object, float]] = {}   # host -> (owner, last request)
        self._lock = threading.Lock()
        self._clock = clock
        self._sleep = sleep
        self._local = threading.local()

    def set_owner(self, owner: object, budget: "FetchBudget | None" = None) -> None:
        """Mark the requests that follow on this thread as one source's
        (and, with ``budget``, never wait past its deadline)."""
        self._local.owner = owner
        self._local.budget = budget

    def reserve(self, host: str, owner: object = None) -> float:
        """Book the next request to host; return how long to wait for it."""
        with self._lock:
            now = self._clock()
            if len(self._last) > 2000:   # forget hosts not used for a while
                self._last = {h: v for h, v in self._last.items()
                              if v[1] + self.interval > now}
            prev = self._last.get(host)
            slot = now
            if prev is not None and (owner is None or prev[0] != owner):
                slot = max(now, prev[1] + self.interval)
            self._last[host] = (owner, slot)
            return slot - now

    def before_request(self, request: httpx.Request) -> None:
        delay = self.reserve(request.url.host or "", getattr(self._local, "owner", None))
        budget = getattr(self._local, "budget", None)
        if budget is not None and budget.left() - delay <= 0.05:
            budget.capped = True
            raise httpx.ConnectTimeout("scan time budget used up", request=request)
        if delay > 0:
            self._sleep(delay)


HOST_GATE = HostGate(HOST_MIN_INTERVAL_SECONDS)
_ssl_ctx: object | None = None
_ssl_lock = threading.Lock()


def _default_verify():
    """One certifi-based context shared by every scan client (cheap per client)."""
    global _ssl_ctx
    with _ssl_lock:
        if _ssl_ctx is None:
            _ssl_ctx = aia.strict_context()
        return _ssl_ctx


class FetchBudget:
    """A deadline shared by every request one fetch makes.

    Each request's connect/read/write/pool timeouts are shortened to the time
    left before ``deadline``, and no request starts after it, so a fetch
    cannot run past the deadline because of robots.txt (5 s), a 10 s slow-lane
    read or a redirect chain. ``capped`` records that the budget, not the
    site, set a timeout: a fetch cut short that way is retried next run
    instead of being recorded as a TIMEOUT failure.
    """

    def __init__(self, deadline: float, clock=time.monotonic) -> None:
        self.deadline = deadline
        self.capped = False
        self._clock = clock

    def left(self) -> float:
        return self.deadline - self._clock()

    def cap(self, request: httpx.Request) -> None:
        left = self.left()
        if left <= 0.05:
            self.capped = True
            raise httpx.ConnectTimeout("scan time budget used up", request=request)
        timeout = dict(request.extensions.get("timeout") or {})
        for key in ("connect", "read", "write", "pool"):
            value = timeout.get(key)
            if value is None or value > left:
                timeout[key] = left
                self.capped = True
        request.extensions["timeout"] = timeout

    def cut_short(self, outcome) -> bool:
        """Did the budget (not the site) end this fetch?"""
        if not self.capped:
            return False
        exc = getattr(outcome, "exc", None)
        return isinstance(exc, httpx.TimeoutException) or self.left() <= 0.25


class _BudgetTransport(httpx.BaseTransport):
    def __init__(self, inner: httpx.BaseTransport, budget: FetchBudget) -> None:
        self._inner = inner
        self._budget = budget

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._budget.cap(request)
        return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()


def make_scan_client(verify=None, read_timeout: float | None = None,
                     budget: FetchBudget | None = None) -> httpx.Client:
    transport: httpx.BaseTransport = httpx.HTTPTransport(
        verify=verify if verify is not None else _default_verify())
    if budget is not None:
        transport = _BudgetTransport(transport, budget)
    return httpx.Client(
        timeout=httpx.Timeout(read_timeout or READ_TIMEOUT_SECONDS,
                              connect=CONNECT_TIMEOUT_SECONDS),
        follow_redirects=True,
        headers={"User-Agent": settings.URL_TEST_USER_AGENT},
        transport=transport,
        event_hooks={"request": [HOST_GATE.before_request]},
    )


def _rows(payload) -> int:
    return len(getattr(payload, "raw_list", None) or [])


class ApplyClock:
    """Estimates how long writing one result takes, learning from this run.

    Until the run has written something it assumes APPLY_BASE_SECONDS plus
    APPLY_PER_VACANCY_SECONDS per vacancy (conservative: about 10 ms per
    statement). After that it uses the slowest write seen in this run, so
    the estimate follows the real database and CPU speed.
    """

    def __init__(self) -> None:
        self._base: float | None = None
        self._per_row: float | None = None

    @property
    def base(self) -> float:
        return APPLY_BASE_SECONDS if self._base is None else self._base

    @property
    def per_row(self) -> float:
        return APPLY_PER_VACANCY_SECONDS if self._per_row is None else self._per_row

    def estimate(self, payload) -> float:
        return self.base + self.per_row * _rows(payload)

    def observe(self, payload, seconds: float) -> None:
        rows = _rows(payload)
        if rows:
            self._per_row = max(self._per_row or 0.0, seconds / rows)
        else:
            self._base = max(self._base or 0.0, seconds)


def host_of(url: str | None) -> str:
    return (urlparse(url or "").hostname or "").lower()


def _fetch_task(snapshot: SourceSnapshot, fetch_deadline: float, fetch_fn, client_factory,
                now: datetime, aia_fn, slow: bool = False) -> tuple[str, object]:
    """Runs on a worker thread. No database access here.

    Returns ("ok", outcome), ("crash", exc), ("no_slot", None) or
    ("no_time", None) when the time budget, not the site, ended the fetch.
    """
    extra = {"read_timeout": SLOW_READ_TIMEOUT_SECONDS} if slow else {}
    wait_for_slot = fetch_deadline - SUBMIT_RESERVE_SECONDS - time.monotonic()
    if not _FETCH_SLOTS.acquire(timeout=max(0.0, wait_for_slot)):
        return "no_slot", None
    budget = FetchBudget(fetch_deadline)
    HOST_GATE.set_owner(snapshot.id, budget)
    try:
        with backoff_retry_cap(1):
            with client_factory(budget=budget, **extra) as client:
                outcome = fetch_fn(snapshot, client, now=now)
            if budget.cut_short(outcome):
                return "no_time", None
            target = aia.incomplete_chain_target(outcome.exc) if outcome.kind == "error" else None
            if target is not None and budget.left() >= AIA_MIN_SECONDS:
                # Each AIA step (leaf, up to three intermediates) gets a fifth of what is left.
                ctx = aia_fn(*target, timeout=min(4.0, budget.left() / 5))
                if ctx is not None and budget.left() > 1.0:
                    with client_factory(verify=ctx, budget=budget, **extra) as client:
                        retry = fetch_fn(snapshot, client, now=now)
                    if budget.cut_short(retry):
                        return "no_time", None
                    retry.started = outcome.started
                    outcome = retry
        return "ok", outcome
    except Exception as exc:  # an adapter bug: the main thread stamps a failure
        if budget.capped and budget.left() <= 0.25:
            return "no_time", None
        return "crash", exc
    finally:
        HOST_GATE.set_owner(None)
        _FETCH_SLOTS.release()


def _default_fetch(snapshot, client, now=None) -> FetchOutcome:
    return fetch_source(snapshot, client, check_robots=True, now=now)


def run_scan_batch(db: Session, limit: int = 60, max_seconds: float = 18.0,
                   workers: int = DEFAULT_WORKERS, now: datetime | None = None,
                   fetch_fn: Callable | None = None,
                   client_factory: Callable | None = None,
                   aia_fn: Callable | None = None) -> dict:
    """Scan due sources; return the JobRun summary within ``max_seconds``.

    ``max_seconds`` covers the whole call: choosing the batch, fetching,
    writing results and un-claiming leftovers. Timeline, counted back from
    the end: requests are cut off WRAPUP_RESERVE_SECONDS before it (the fetch
    deadline); new fetches start only while SUBMIT_RESERVE_SECONDS remain
    before the fetch deadline; results are written only while their estimated
    write time fits before RELEASE_RESERVE_SECONDS; then one commit un-claims
    whatever was not written.

    ``fetch_fn(snapshot, client, now=...)`` runs on worker threads and must
    not touch the database; it defaults to fetch_source with robots.txt on.
    """
    fetch_fn = fetch_fn or _default_fetch
    client_factory = client_factory or make_scan_client
    aia_fn = aia_fn or aia.context_for
    started = time.monotonic()
    end = started + max_seconds
    fetch_deadline = end - WRAPUP_RESERVE_SECONDS
    submit_until = fetch_deadline - SUBMIT_RESERVE_SECONDS
    write_until = end - RELEASE_RESERVE_SECONDS
    now = now or datetime.now(timezone.utc)
    queue: deque[DueItem] = deque(select_due(db, limit, now))
    selected = len(queue)
    inflight: dict = {}             # future -> (item, source_id, previous)
    inflight_hosts: set[str] = set()
    to_release: list[tuple[str, datetime | None]] = []
    scanned = created = failed = skipped_claimed = 0
    stopped_early = False
    executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="scan")

    def next_item() -> DueItem | None:
        left = fetch_deadline - time.monotonic()
        for i, item in enumerate(queue):
            if item.slow and left < SLOW_SUBMIT_RESERVE_SECONDS:
                continue
            if host_of(item.url) not in inflight_hosts:
                del queue[i]
                return item
        return None

    def claim(item: DueItem) -> VacancySource | None:
        with _CLAIM_LOCK:
            if item.source_id is None:
                company = db.get(Company, item.company_id)
                if company is None:
                    return None
                source = ensure_source(db, company)
                if source is None:
                    return None
                token = source.last_checked
                if token is not None and item.last_scanned is None:
                    return None        # someone created and scanned it meanwhile
                ok = claim_source(db, source.id, token, now)
            else:
                ok = claim_source(db, item.source_id, item.claim_token, now)
                source = db.get(VacancySource, item.source_id) if ok else None
        if not ok:
            return None
        db.refresh(source)
        return source

    def apply(item: DueItem, source_id: str, status: str, payload) -> None:
        nonlocal scanned, created, failed
        try:
            if status != "ok":
                raise payload if isinstance(payload, BaseException) else RuntimeError(status)
            source = db.get(VacancySource, source_id)
            report = apply_fetch(db, source, payload)
            company = db.get(Company, item.company_id)
            if company is not None:
                company.last_checked = now
            db.commit()
            scanned += 1
            created += report.created
            if report.status not in ("ok", "empty"):
                failed += 1
        except Exception:
            # A failed INSERT aborts the transaction: roll back, stamp, continue.
            logger.warning("scan_due_companies: failed to scan company %s", item.company_id,
                           exc_info=True)
            scanned += 1
            failed += 1
            try:
                _stamp_failure(db, item.company_id, now)
            except Exception:
                logger.warning("scan_due_companies: could not stamp failure for %s",
                               item.company_id, exc_info=True)
                db.rollback()

    cut_short = 0
    apply_clock = ApplyClock()
    try:
        while True:
            while queue and len(inflight) < workers and time.monotonic() < submit_until:
                item = next_item()
                if item is None:
                    break
                source = claim(item)
                if source is None:
                    skipped_claimed += 1
                    continue
                fut = executor.submit(_fetch_task, snapshot_of(source), fetch_deadline, fetch_fn,
                                      client_factory, now, aia_fn, item.slow)
                inflight[fut] = (item, source.id, item.claim_token)
                inflight_hosts.add(host_of(item.url))
            if queue and time.monotonic() >= submit_until:
                stopped_early = True
            if not inflight:
                if queue:
                    stopped_early = True   # only slow sources left, too late to start them
                break
            remaining = min(fetch_deadline + FETCH_GRACE_SECONDS, write_until) - time.monotonic()
            if remaining <= 0:
                stopped_early = True
                break
            done, _ = wait(list(inflight), timeout=remaining, return_when=FIRST_COMPLETED)
            for fut in done:
                item, source_id, previous = inflight.pop(fut)
                inflight_hosts.discard(host_of(item.url))
                status, payload = fut.result()
                if status in ("no_slot", "no_time"):
                    cut_short += status == "no_time"
                    to_release.append((source_id, previous))
                    stopped_early = True
                    continue
                if time.monotonic() + apply_clock.estimate(payload) > write_until:
                    to_release.append((source_id, previous))
                    stopped_early = True
                    continue
                t_apply = time.monotonic()
                apply(item, source_id, status, payload)
                apply_clock.observe(payload, time.monotonic() - t_apply)
    finally:
        abandoned = len(inflight)
        to_release.extend((source_id, previous) for item, source_id, previous in inflight.values())
        if abandoned:
            stopped_early = True
        executor.shutdown(wait=False, cancel_futures=True)
        if to_release:
            try:
                release_claims(db, to_release, now)
            except Exception:
                logger.warning("scan_due_companies: could not release %d claims", len(to_release),
                               exc_info=True)
                db.rollback()
    return {
        "batch_limit": limit, "due_selected": selected, "companies_scanned": scanned,
        "vacancies_created": created, "sources_failed": failed,
        "skipped_already_claimed": skipped_claimed, "abandoned_in_flight": abandoned,
        "released_unfinished": len(to_release), "cut_short_by_budget": cut_short,
        "candidates_alerted": 0, "stopped_early_on_time_budget": stopped_early,
        "elapsed_seconds": round(time.monotonic() - started, 1), "budget_seconds": max_seconds,
        "write_seconds_base": round(apply_clock.base, 3),
        "write_seconds_per_vacancy": round(apply_clock.per_row, 4),
        "workers": workers,
    }
