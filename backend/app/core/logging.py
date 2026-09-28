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


def _redact(value):
    if isinstance(value, str):
        return _EMAIL.sub("[redacted-email]", value)
    return value


class RedactEmailFilter(logging.Filter):
    """Strip email-shaped strings from log records before they hit stdout."""

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

    _init_sentry()


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
    )
    log.info("Sentry error tracking initialised (env=%s)", settings.ENV)
