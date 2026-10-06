"""Centralized logging + optional error tracking (observability).

The codebase previously had zero structured logging anywhere — failures in
the many `except Exception: pass` blocks scattered across services vanished
with no trace, and the only production visibility was Render's raw stdout
capture plus the JobRun audit trail for scheduled jobs specifically.

This module gives every module a real logger that lands in Render's log
stream (a plain StreamHandler on stdout is enough — Render captures and
makes that searchable, no shipping infrastructure needed), and an optional
Sentry hook for real error tracking/alerting: set SENTRY_DSN and it turns
on automatically; leave it unset and this is a no-op.
"""
from __future__ import annotations

import logging
import re
import sys

from app.core.config import settings

_CONFIGURED = False
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


# Query-string parameters whose values are secrets. Matches the name anywhere in
# the parameter (token, reset_token, access_token, api_key, signature, code, ...).
# Over-redacting a harmless parameter is fine; logging a live token is not.
_SECRET_PARAM = re.compile(
    r"(?i)([?&;][^=&\s\"'#?]*?(?:token|code|key|secret|signature|sig|password|passwd|otp|jwt|auth|credential)"
    r"[^=&\s\"'#?]*=)[^&\s\"'#]*"
)
# A JWT anywhere in a line (e.g. pasted into a path), not just after ?token=.
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
REDACTED = "[redacted]"


def scrub_secrets(text: str) -> str:
    """Remove secret query values and bare JWTs from a log line or URL."""
    if "=" in text:
        text = _SECRET_PARAM.sub(lambda m: m.group(1) + REDACTED, text)
    if "eyJ" in text:
        text = _JWT.sub("[redacted-jwt]", text)
    return text


def _redact(value):
    if isinstance(value, str):
        return scrub_secrets(_EMAIL.sub("[redacted-email]", value))
    return value


class RedactEmailFilter(logging.Filter):
    """Strip email-shaped strings, secret query values (?token=...) and JWTs
    from log records before they hit stdout. uvicorn's access log passes the
    request path *with* its query string as an argument, e.g.
    ``GET /api/v1/auth/verify?token=eyJ...`` -- that is what this catches."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: _redact(v) for k, v in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(_redact(a) for a in record.args)
        return True


def configure_logging() -> None:
    """Set up the root logger. Idempotent — safe to call more than once
    (e.g. once from app/main.py at import time, again from a test fixture)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    level = logging.INFO if settings.ENV == "production" else logging.DEBUG
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        ))
        handler.addFilter(RedactEmailFilter())
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            if not any(isinstance(f, RedactEmailFilter) for f in handler.filters):
                handler.addFilter(RedactEmailFilter())

    install_uvicorn_scrubbers()
    _init_sentry()


_UVICORN_LOGGERS = ("uvicorn.access", "uvicorn.error", "uvicorn")


def install_uvicorn_scrubbers() -> None:
    """Attach the redacting filter to uvicorn's own loggers (idempotent).

    uvicorn's loggers don't propagate to the root logger, so the root handler's
    filter never sees the access log. A filter on the *logger* survives
    uvicorn's dictConfig (which replaces handlers, not logger filters); it is
    also put on their current handlers. Called at import and again at startup.
    """
    for name in _UVICORN_LOGGERS:
        target = logging.getLogger(name)
        for obj in (target, *target.handlers):
            if not any(isinstance(f, RedactEmailFilter) for f in obj.filters):
                obj.addFilter(RedactEmailFilter())


def _sentry_before_send(event, hint):
    """Same scrubbing for Sentry events: the request URL and query string."""
    request = event.get("request") or {}
    if isinstance(request.get("url"), str):
        request["url"] = scrub_secrets(request["url"])
    if isinstance(request.get("query_string"), str):
        request["query_string"] = scrub_secrets("?" + request["query_string"])[1:]
    return event


def _init_sentry() -> None:
    """Opt-in error tracking. A no-op unless SENTRY_DSN is set, so this never
    changes behaviour for a deployment that hasn't configured it."""
    dsn = settings.SENTRY_DSN
    if not dsn:
        return
    log = logging.getLogger(__name__)
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        log.warning(
            "SENTRY_DSN is set but sentry-sdk isn't installed — "
            "add sentry-sdk[fastapi] to requirements.txt to enable it."
        )
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.ENV,
        integrations=[
            FastApiIntegration(),
            # Every logger.error()/logger.exception() call also becomes a
            # Sentry event; plain info/debug logs are left as breadcrumbs.
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.0,  # error tracking only, no perf tracing by default
        before_send=_sentry_before_send,
    )
    log.info("Sentry error tracking initialised (env=%s)", settings.ENV)
