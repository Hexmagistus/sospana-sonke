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
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.ENV != "test")
