"""Keep the single uvicorn process's resident memory flat.

The Render memory graph climbed in steps during busy periods and never came
back down (319 -> 387 MB in 24 h on a 512 MB instance). Python's own heap was
flat (tracemalloc: +0.3 MB over 60 directory-page bursts), so the growth is
native: concurrent requests run on many threadpool threads, glibc gives
threads their own malloc arenas (up to 8 x CPU count), and freed memory stays
parked there. Capping arenas and trimming after jobs keeps RSS flat; the
bigger win is that icon requests no longer use the threadpool at all (see
app/services/icon_cache.py).

``MALLOC_ARENA_MAX`` in the environment does the same thing and wins if set.
Both helpers are no-ops on non-glibc platforms (macOS, musl, Windows).
"""
from __future__ import annotations

import ctypes
import ctypes.util
import gc
import logging
import os
import sys

logger = logging.getLogger(__name__)

_M_ARENA_MAX = -8  # from glibc malloc.h
DEFAULT_ARENA_MAX = 2


def _libc():
    if not sys.platform.startswith("linux"):
        return None
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
        libc.mallopt  # noqa: B018 -- glibc only; musl has no mallopt
        libc.malloc_trim  # noqa: B018
        return libc
    except (OSError, AttributeError):
        return None


def limit_malloc_arenas(n: int = DEFAULT_ARENA_MAX) -> bool:
    """Cap glibc malloc arenas for threads created from now on.

    Called once at import of app.main, before uvicorn starts the threadpool.
    Respects an explicit MALLOC_ARENA_MAX env var (glibc already applied it).
    """
    if os.environ.get("MALLOC_ARENA_MAX"):
        return False
    libc = _libc()
    if libc is None:
        return False
    try:
        return bool(libc.mallopt(_M_ARENA_MAX, int(n)))
    except Exception:  # never let a tuning call stop the app from starting
        logger.debug("mallopt(M_ARENA_MAX) failed", exc_info=True)
        return False


def trim_heap() -> bool:
    """Collect garbage and hand free heap pages back to the OS (glibc only).

    Cheap enough to run after a scheduled job (a few ms), not per request.
    """
    gc.collect()
    libc = _libc()
    if libc is None:
        return False
    try:
        return bool(libc.malloc_trim(0))
    except Exception:
        logger.debug("malloc_trim failed", exc_info=True)
        return False


def current_rss_mb() -> float | None:
    """Resident set size of this process in MB (Linux), else None."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        return None
    return None
