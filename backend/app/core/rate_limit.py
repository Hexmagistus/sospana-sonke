"""Shared rate-limiting configuration (blueprint security hardening).

A single Limiter instance is used across the app so all decorated routes share
one clock/store. Keyed by client IP by default -- fine behind Render's single
reverse proxy (no shared NAT of many distinct legitimate users to worry about
at our current scale). Disabled under the test suite: the FastAPI `app` object
is a single import-time singleton reused by every test in the whole pytest
run (see tests/conftest.py), so per-IP counters would otherwise accumulate
across hundreds of unrelated test cases and cause flaky, unrelated failures.
"""
from slowapi import Limiter

from app.core.client_ip import client_ip
from app.core.config import settings

# Keyed on the real client IP (see app/core/client_ip.py) -- NOT
# slowapi.util.get_remote_address, which behind Render's proxy returns the
# proxy's own address and turned every per-IP limit into one global bucket.
limiter = Limiter(key_func=client_ip, enabled=settings.ENV != "test")


def user_or_ip_key(request) -> str:
    """Key authenticated bulk-read limits on the account, not the IP, so one
    scraper account can't rotate IPs to escape its budget (and many people on
    one shared campus/office IP don't share a bucket). Falls back to IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from app.core.security import decode_token
            sub = decode_token(auth[7:].strip(), expected_type="access").get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return f"ip:{client_ip(request)}"
