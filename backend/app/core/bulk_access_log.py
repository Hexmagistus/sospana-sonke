"""One JSON line per call to a bulk/list endpoint: IP, user agent, account,
path, query and status. Lets a future bulk copy be traced to an IP/account.
Render keeps these in its log stream; search for "bulk_access"."""
import json
import logging

from app.core.client_ip import client_ip
from app.core.rate_limit import user_or_ip_key

log = logging.getLogger("app.bulk_access")

BULK_PREFIXES = (
    "/api/v1/employers", "/api/v1/companies", "/api/v1/jobs",
)


def is_bulk(path: str) -> bool:
    return path.startswith(BULK_PREFIXES)


def bulk_line(request, status: int) -> str:
    key = user_or_ip_key(request)
    return json.dumps({
        "event": "bulk_access",
        "ip": client_ip(request),
        "account": key[5:] if key.startswith("user:") else None,
        "ua": (request.headers.get("user-agent") or "")[:200],
        "path": request.url.path,
        "query": str(request.url.query)[:300],
        "status": status,
        "internal": bool(request.headers.get("x-internal-key")),
    })
