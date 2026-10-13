"""Tell IndexNow that the public role pages changed.

The key is public (it is also a file on the site). An empty key does nothing,
and a failed ping never stops the job that asked for it. One process pings at
most once every six hours.
"""
from __future__ import annotations

import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
_last_ping = 0.0


def ping_indexnow(urls: list[str] | None = None) -> bool:
    global _last_ping
    key = (settings.INDEXNOW_KEY or "").strip()
    if not key or settings.ENV == "test":
        return False
    now = time.monotonic()
    if _last_ping and now - _last_ping < 6 * 3600:
        return False
    site = (settings.PUBLIC_SITE_URL or "https://sospana-sonke.vercel.app").rstrip("/")
    host = site.split("://", 1)[-1]
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"{site}/{key}.txt",
        "urlList": urls or [
            f"{site}/jobs",
            f"{site}/opportunities",
            f"{site}/feed.xml",
        ],
    }
    try:
        response = httpx.post("https://api.indexnow.org/indexnow", json=payload, timeout=5.0)
    except Exception:
        logger.info("indexnow ping failed")
        return False
    _last_ping = now
    return response.status_code in (200, 202)
