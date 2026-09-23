"""Resolve the real client IP behind Render's reverse proxy.

uvicorn only trusts X-Forwarded-For from 127.0.0.1 by default, so behind
Render's load balancer `request.client.host` is the *proxy's* internal address
-- the same value for every visitor. Rate limits keyed on it were effectively
global: ten failed logins from anyone locked out login for everyone, and a
single attacker was indistinguishable from the whole user base.

X-Forwarded-For is a comma-separated chain. A client can put anything it likes
at the *front* of that chain, but each trusted proxy appends the address it saw
at the *end*. So the trustworthy entry is the one `TRUSTED_PROXY_HOPS` from the
right (1 = the address Render's edge saw connecting to it). Never take the
left-most entry: it is attacker-controlled.
"""
from __future__ import annotations

import ipaddress

from app.core.config import settings


def _valid_ip(value: str) -> str | None:
    value = value.strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def client_ip(request) -> str:
    hops = settings.TRUSTED_PROXY_HOPS
    if hops > 0:
        chain = [p for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(chain) >= hops:
            ip = _valid_ip(chain[-hops])
            if ip:
                return ip
    return request.client.host if request.client else "unknown"
