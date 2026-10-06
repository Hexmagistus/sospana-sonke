"""Cheap serving of company icons.

GET /companies/{id}/icon is requested once per directory card, so a single
page can fire 100+ at once. Before this module every one of those opened a
DB session and loaded the whole company row (icon bytes included) on a
threadpool thread; with a 5+2 connection pool a burst queued behind the pool,
filled uvicorn's ``--limit-concurrency 40`` and turned icons *and* /health
into 503s (94 in one minute on 2026-10-06).

Now:
- One query loads a small index of every company's icon facts (legacy URL,
  whether bytes are stored, MIME, version). Icon requests are answered from
  that index without touching the DB. It is rebuilt after
  ``INDEX_TTL_SECONDS``.
- Stored icon bytes are fetched one company at a time, at most
  ``MAX_CONCURRENT_DB_LOADS`` at once, and kept in a byte-capped LRU keyed by
  (company, version).
- An id that isn't in the index (unknown, deleted, or created after the last
  rebuild) is looked up once and the answer, including "not found", is cached.
- The directory sends ``?v=<icon_version>`` (from the list response). When
  that is newer than what we hold (the icon job stored a new icon since the
  last rebuild) the one company is re-read from the DB, at most once per
  ``RECHECK_SECONDS`` per company, so a made-up ``v`` cannot be used to make
  every request hit the database. This is why the icon job itself does not
  need to tell this cache anything.

Every structure here has an entry cap, a byte cap (or a fixed small row size)
and a TTL. Nothing grows with traffic.
"""
from __future__ import annotations

import hashlib
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timezone

from sqlalchemy import select

from app.core.bounded_cache import BoundedTTLCache
from app.models.company import Company

INDEX_TTL_SECONDS = 600.0
# Hard ceiling on the index (production has ~5.7k companies, ~150 bytes of
# facts each). Past this the index is not kept and every request uses the
# bounded per-id path instead.
INDEX_MAX_ENTRIES = 20_000
MAX_CONCURRENT_DB_LOADS = 3
RECHECK_SECONDS = 60.0


def _facts_size(v) -> int:
    return 120 + len((v and v.url) or "")


# Icon bytes: favicons are 1-20 KB (the icon job caps them). 8 MB holds a few hundred.
icon_bytes_cache = BoundedTTLCache(max_entries=2_000, max_bytes=8 * 1024 * 1024,
                                   ttl_seconds=3_600.0,
                                   sizeof=lambda v: len(v.data) + 200)
# Per-id facts read after the last index rebuild (ids the index didn't have,
# including negative "no such company", and versioned re-checks).
_lookup_cache = BoundedTTLCache(max_entries=5_000, max_bytes=2 * 1024 * 1024,
                                ttl_seconds=INDEX_TTL_SECONDS, sizeof=_facts_size)
# Which ids were re-read for a newer ?v= recently (rate limit for that path).
_recheck_marks = BoundedTTLCache(max_entries=5_000, max_bytes=512 * 1024,
                                 ttl_seconds=RECHECK_SECONDS, sizeof=lambda v: 64)


class _Miss:
    pass


_MISS = _Miss()

db_load_slots = threading.BoundedSemaphore(MAX_CONCURRENT_DB_LOADS)


@dataclass(frozen=True)
class IconFacts:
    url: str | None          # legacy URL (redirect target) when no bytes are stored
    has_data: bool
    mime: str | None
    version: int             # favicon_checked_at as epoch seconds, 0 if never


@dataclass(frozen=True)
class IconBytes:
    data: bytes
    mime: str
    etag: str


@contextmanager
def session_from_dependency(dependency):
    """Open a session the way a FastAPI generator dependency (get_db) does."""
    gen = dependency()
    try:
        yield next(gen)
    finally:
        gen.close()


def icon_version(checked_at) -> int:
    """Changes whenever the icon job re-checks a company (it stamps
    favicon_checked_at on every attempt, and always when it stores new bytes).
    The frontend puts it in the icon URL (?v=), which is what makes the long
    immutable cache safe."""
    if checked_at is None:
        return 0
    if checked_at.tzinfo is None:  # SQLite drops the zone; values are written as UTC
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    return int(checked_at.timestamp())


def parse_version(v: str | None) -> int | None:
    if v is None or not v.isdigit() or len(v) > 12:
        return None
    return int(v)


class _Index:
    def __init__(self) -> None:
        self._facts: dict[str, IconFacts] | None = None
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def fresh(self) -> bool:
        return self._facts is not None and time.monotonic() - self._loaded_at < INDEX_TTL_SECONDS

    def get(self, company_id: str):
        facts = self._facts
        return None if facts is None else facts.get(company_id)

    def load(self, session_factory) -> None:
        """Rebuild from one query. Single-flight: concurrent callers wait, then reuse."""
        with self._lock:
            if self.fresh():
                return
            with db_load_slots:
                with session_factory() as db:
                    rows = db.execute(
                        select(Company.id, Company.favicon_url, Company.favicon_mime,
                               Company.favicon_checked_at, Company.favicon_data.isnot(None))
                        .where(Company.deleted_at.is_(None))
                        .limit(INDEX_MAX_ENTRIES + 1)
                    ).all()
            if len(rows) > INDEX_MAX_ENTRIES:
                facts: dict[str, IconFacts] = {}
            else:
                facts = {
                    cid: IconFacts(url=(url or None), has_data=bool(has_data), mime=mime,
                                   version=icon_version(checked))
                    for cid, url, mime, checked, has_data in rows
                }
            # The rebuilt index is at least as new as every per-id answer.
            _lookup_cache.clear()
            self._facts, self._loaded_at = facts, time.monotonic()

    def clear(self) -> None:
        with self._lock:
            self._facts = None
            self._loaded_at = 0.0

    def __len__(self) -> int:
        return len(self._facts or {})


icon_index = _Index()


def _from_memory(company_id: str):
    """IconFacts, None (known not to exist), or _MISS (memory can't say)."""
    found = _lookup_cache.get(company_id, default=_MISS)
    if found is not _MISS:
        return found
    if icon_index.fresh():
        facts = icon_index.get(company_id)
        if facts is not None:
            return facts
    return _MISS


def _needs_recheck(company_id: str, facts, want_version: int | None) -> bool:
    """True when the URL asks for a newer icon than we hold and we haven't
    re-read this company in the last RECHECK_SECONDS."""
    if want_version is None:
        return False
    held = facts.version if facts is not None else -1
    if want_version <= held:
        return False
    return _recheck_marks.get(company_id) is None


def _read_one(company_id: str, session_factory) -> IconFacts | None:
    with db_load_slots:
        with session_factory() as db:
            row = db.execute(
                select(Company.favicon_url, Company.favicon_mime, Company.favicon_checked_at,
                       Company.favicon_data.isnot(None))
                .where(Company.id == company_id, Company.deleted_at.is_(None))
            ).first()
    found = None if row is None else IconFacts(url=(row[0] or None), has_data=bool(row[3]),
                                               mime=row[1], version=icon_version(row[2]))
    _lookup_cache.set(company_id, found)
    return found


def facts_for(company_id: str, session_factory, want_version: int | None = None) -> IconFacts | None:
    """Icon facts for a company, or None when it doesn't exist / is deleted."""
    if not icon_index.fresh():
        icon_index.load(session_factory)
    facts = _from_memory(company_id)
    if facts is _MISS:
        return _read_one(company_id, session_factory)
    if _needs_recheck(company_id, facts, want_version):
        _recheck_marks.set(company_id, True)
        return _read_one(company_id, session_factory)
    return facts


def bytes_for(company_id: str, facts: IconFacts, session_factory) -> IconBytes | None:
    key = (company_id, facts.version)
    cached = icon_bytes_cache.get(key)
    if cached is not None:
        return cached
    with db_load_slots:
        with session_factory() as db:
            row = db.execute(
                select(Company.favicon_data, Company.favicon_mime)
                .where(Company.id == company_id, Company.deleted_at.is_(None))
            ).first()
    if row is None or not row[0]:
        return None
    data = bytes(row[0])
    icon = IconBytes(data=data, mime=row[1] or facts.mime or "image/png",
                     etag='"' + hashlib.sha256(data).hexdigest()[:20] + '"')
    icon_bytes_cache.set(key, icon)
    return icon


def cached_without_db(company_id: str, want_version: int | None = None):
    """(facts, bytes) when the request can be answered from memory, else None."""
    if not icon_index.fresh():
        return None
    facts = _from_memory(company_id)
    if facts is _MISS or _needs_recheck(company_id, facts, want_version):
        return None
    if facts is not None and facts.has_data:
        icon = icon_bytes_cache.get((company_id, facts.version))
        if icon is None:
            return None
        return facts, icon
    return facts, None


def invalidate_icons() -> None:
    """Drop everything (tests, or after a bulk change made outside the icon job)."""
    icon_index.clear()
    icon_bytes_cache.clear()
    _lookup_cache.clear()
    _recheck_marks.clear()


def stats() -> dict:
    return {"index_entries": len(icon_index), "index_fresh": icon_index.fresh(),
            "bytes": icon_bytes_cache.stats(), "lookups": _lookup_cache.stats(),
            "rechecks": _recheck_marks.stats()}
