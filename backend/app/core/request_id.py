"""One id per request, echoed on the response and written as one JSON line."""
from __future__ import annotations

import json
import logging
import re
import time
import uuid

from app.core.logging import scrub_secrets

_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
access_log = logging.getLogger("app.access")


def request_id_from(header: str | None) -> str:
    """Keep a caller-supplied id when it is a short token. Otherwise mint one."""
    if header:
        candidate = header.strip()
        if _ID.match(candidate):
            return candidate
    return uuid.uuid4().hex


def access_line(request_id: str, method: str, path: str, status: int, duration_ms: float) -> str:
    """One JSON object. The path is scrubbed. The query string is not included."""
    return json.dumps(
        {
            "request_id": request_id,
            "method": method,
            "path": scrub_secrets(path),
            "status": status,
            "duration_ms": duration_ms,
        },
        separators=(",", ":"),
    )


class RequestTimer:
    def __init__(self) -> None:
        self.started = time.perf_counter()

    def elapsed_ms(self) -> float:
        return round((time.perf_counter() - self.started) * 1000, 1)
