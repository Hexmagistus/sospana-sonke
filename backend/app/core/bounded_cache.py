"""A small, thread-safe in-process cache with hard limits.

Every in-process cache in the API goes through this (or is a single slot with
a TTL), so memory on the 512 MB Render instance can't grow with traffic:

- ``max_entries``: least-recently-used entries are evicted past this count.
- ``max_bytes``: an approximate byte budget, using the ``sizeof`` callback
  (default: ``len()`` of bytes/str values, else a flat 256). An entry larger
  than the whole budget is never stored.
- ``ttl_seconds``: an entry older than this is a miss and is dropped.

No Redis or other service: this is per process, which is fine on one worker.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Hashable

_MISSING = object()


def _default_sizeof(value: Any) -> int:
    if isinstance(value, (bytes, bytearray, memoryview, str)):
        return len(value) + 64
    return 256


class BoundedTTLCache:
    def __init__(self, *, max_entries: int, max_bytes: int, ttl_seconds: float,
                 sizeof: Callable[[Any], int] | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if max_entries < 1 or max_bytes < 1 or ttl_seconds <= 0:
            raise ValueError("cache limits must be positive")
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.ttl_seconds = ttl_seconds
        self._sizeof = sizeof or _default_sizeof
        self._clock = clock
        self._data: OrderedDict[Hashable, tuple[float, int, Any]] = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: Hashable, default: Any = None) -> Any:
        with self._lock:
            item = self._data.get(key, _MISSING)
            if item is _MISSING:
                self.misses += 1
                return default
            stored_at, size, value = item
            if self._clock() - stored_at >= self.ttl_seconds:
                del self._data[key]
                self._bytes -= size
                self.misses += 1
                return default
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: Hashable, value: Any) -> bool:
        """Store ``value``. Returns False when it is too big to cache at all."""
        size = max(1, int(self._sizeof(value)))
        with self._lock:
            old = self._data.pop(key, None)
            if old is not None:
                self._bytes -= old[1]
            if size > self.max_bytes:
                return False
            self._data[key] = (self._clock(), size, value)
            self._bytes += size
            while len(self._data) > self.max_entries or self._bytes > self.max_bytes:
                _, (_, evicted_size, _) = self._data.popitem(last=False)
                self._bytes -= evicted_size
                self.evictions += 1
            return True

    def invalidate(self, key: Hashable) -> None:
        with self._lock:
            old = self._data.pop(key, None)
            if old is not None:
                self._bytes -= old[1]

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._bytes = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    @property
    def total_bytes(self) -> int:
        with self._lock:
            return self._bytes

    def stats(self) -> dict:
        with self._lock:
            return {"entries": len(self._data), "bytes": self._bytes,
                    "max_entries": self.max_entries, "max_bytes": self.max_bytes,
                    "ttl_seconds": self.ttl_seconds, "hits": self.hits,
                    "misses": self.misses, "evictions": self.evictions}
