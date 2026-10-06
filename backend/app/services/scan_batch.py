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
  or timed out last time, started only while 16 s remain). No fetch starts with less than
  SUBMIT_RESERVE_SECONDS left; the call returns at ``max_seconds`` and abandons
  (and un-claims) whatever is still in flight.
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
    DueItem, _stamp_failure, claim_source, release_claim, select_due,
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
SLOW_SUBMIT_RESERVE_SECONDS = 16.0
SUBMIT_RESERVE_SECONDS = 9.0     # a fetch is robots.txt + one page; leave room for both
APPLY_GRACE_SECONDS = 2.0        # finish writing results that are already in
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

    def set_owner(self, owner: object) -> None:
        """Mark the requests that follow on this thread as one source's."""
        self._local.owner = owner

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


def make_scan_client(verify=None, read_timeout: float | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(read_timeout or READ_TIMEOUT_SECONDS,
                              connect=CONNECT_TIMEOUT_SECONDS),
        follow_redirects=True,
        headers={"User-Agent": settings.URL_TEST_USER_AGENT},
        verify=verify if verify is not None else _default_verify(),
        event_hooks={"request": [HOST_GATE.before_request]},
    )


def host_of(url: str | None) -> str:
    return (urlparse(url or "").hostname or "").lower()


def _fetch_task(snapshot: SourceSnapshot, deadline: float, fetch_fn, client_factory,
                now: datetime, aia_fn, slow: bool = False) -> tuple[str, object]:
    """Runs on a worker thread. No database access here."""
    extra = {"read_timeout": SLOW_READ_TIMEOUT_SECONDS} if slow else {}
    if not _FETCH_SLOTS.acquire(timeout=max(0.0, deadline - SUBMIT_RESERVE_SECONDS - time.monotonic())):
        return "no_slot", None
    HOST_GATE.set_owner(snapshot.id)
    try:
        with backoff_retry_cap(1):
            with client_factory(**extra) as client:
                outcome = fetch_fn(snapshot, client, now=now)
            target = aia.incomplete_chain_target(outcome.exc) if outcome.kind == "error" else None
            if target is not None and time.monotonic() < deadline - SUBMIT_RESERVE_SECONDS / 2:
                ctx = aia_fn(*target)
                if ctx is not None:
                    with client_factory(verify=ctx, **extra) as client:
                        retry = fetch_fn(snapshot, client, now=now)
                    retry.started = outcome.started
                    outcome = retry
        return "ok", outcome
    except Exception as exc:  # an adapter bug: the main thread stamps a failure
        return "crash", exc
    finally:
        HOST_GATE.set_owner(None)
        _FETCH_SLOTS.release()


def _default_fetch(snapshot, client, now=None) -> FetchOutcome:
    return fetch_source(snapshot, client, check_robots=True, now=now)


def run_scan_batch(db: Session, limit: int = 60, max_seconds: float = 22.0,
                   workers: int = DEFAULT_WORKERS, now: datetime | None = None,
                   fetch_fn: Callable | None = None,
                   client_factory: Callable | None = None,
                   aia_fn: Callable | None = None) -> dict:
    """Scan due sources until ``max_seconds``; return the JobRun summary.

    ``fetch_fn(snapshot, client, now=...)`` runs on worker threads and must
    not touch the database; it defaults to fetch_source with robots.txt on.
    """
    fetch_fn = fetch_fn or _default_fetch
    client_factory = client_factory or make_scan_client
    aia_fn = aia_fn or aia.context_for
    started = time.monotonic()
    deadline = started + max_seconds
    submit_until = deadline - SUBMIT_RESERVE_SECONDS
    now = now or datetime.now(timezone.utc)
    queue: deque[DueItem] = deque(select_due(db, limit, now))
    selected = len(queue)
    inflight: dict = {}             # future -> (item, source_id, previous)
    inflight_hosts: set[str] = set()
    scanned = created = failed = skipped_claimed = 0
    stopped_early = False
    executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="scan")

    def next_item() -> DueItem | None:
        left = deadline - time.monotonic()
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
                fut = executor.submit(_fetch_task, snapshot_of(source), deadline, fetch_fn,
                                      client_factory, now, aia_fn, item.slow)
                inflight[fut] = (item, source.id, item.claim_token)
                inflight_hosts.add(host_of(item.url))
            if queue and time.monotonic() >= submit_until:
                stopped_early = True
            if not inflight:
                if queue:
                    stopped_early = True   # only slow sources left, too late to start them
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stopped_early = True
                break
            done, _ = wait(list(inflight), timeout=remaining, return_when=FIRST_COMPLETED)
            for fut in done:
                item, source_id, previous = inflight.pop(fut)
                inflight_hosts.discard(host_of(item.url))
                status, payload = fut.result()
                if status == "no_slot":
                    release_claim(db, source_id, now, previous)
                    queue.appendleft(item)
                    continue
                if time.monotonic() > deadline + APPLY_GRACE_SECONDS:
                    release_claim(db, source_id, now, previous)
                    stopped_early = True
                    continue
                apply(item, source_id, status, payload)
    finally:
        abandoned = len(inflight)
        for fut, (item, source_id, previous) in list(inflight.items()):
            try:
                release_claim(db, source_id, now, previous)
            except Exception:
                logger.warning("scan_due_companies: could not release %s", source_id, exc_info=True)
                db.rollback()
        if abandoned:
            stopped_early = True
        executor.shutdown(wait=False, cancel_futures=True)
    return {
        "batch_limit": limit, "due_selected": selected, "companies_scanned": scanned,
        "vacancies_created": created, "sources_failed": failed,
        "skipped_already_claimed": skipped_claimed, "abandoned_in_flight": abandoned,
        "candidates_alerted": 0, "stopped_early_on_time_budget": stopped_early,
        "elapsed_seconds": round(time.monotonic() - started, 1), "workers": workers,
    }
