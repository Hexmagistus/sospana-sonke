"""Lightweight page-change detection for careers links that aren't
structured-vacancy-scrapable (an extension of blueprint section 31's
alerting, alongside app/services/scan_service.py).

Most companies in the database -- especially the universities added across
Africa, whose careers link is often just their own homepage or news feed
rather than a Greenhouse/Lever-style job board -- can't be parsed into
individual Vacancy rows by app/scraper. This gives them a cheaper honesty
signal instead: fetch the page, hash its visible text, and flag when the
hash changes, so "last verified" and "updated recently" are real, not
guessed. Uses a sync httpx.Client, mirroring scan_service.py's convention,
since this also runs from the plain (sync) scheduler jobs in
app/scheduler/jobs.py.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _normalise(html: str) -> str:
    """Strip tags and collapse whitespace so incidental page noise (a
    rendered timestamp, an ad slot, a view counter) doesn't register as a
    "change" on every single check."""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", html)).strip()


def hash_page_content(html: str) -> str:
    return hashlib.sha256(_normalise(html).encode("utf-8", errors="ignore")).hexdigest()


def make_client() -> httpx.Client:
    return httpx.Client(timeout=settings.URL_TEST_TIMEOUT_SECONDS, follow_redirects=True,
                        headers={"User-Agent": settings.URL_TEST_USER_AGENT})


def check_company_content(company: Company, client: httpx.Client | None = None) -> bool:
    """Fetch the company's careers page and update its hash/checked timestamp
    in place. Returns True if the content changed since the last check --
    always False on the very first check for a company, since there's
    nothing yet to compare against. Caller is responsible for committing."""
    now = datetime.now(timezone.utc)
    company.content_checked_at = now
    if not company.careers_url:
        return False

    owns_client = client is None
    if owns_client:
        client = make_client()
    try:
        resp = client.get(company.careers_url)
        if resp.status_code >= 400:
            return False
        new_hash = hash_page_content(resp.text)
    except Exception:
        return False
    finally:
        if owns_client:
            client.close()

    changed = company.content_hash is not None and new_hash != company.content_hash
    company.content_hash = new_hash
    if changed:
        company.content_changed_at = now
    return changed


def notify_watchers_of_change(db: Session, company: Company) -> int:
    """Email every watcher whose scope matches this company. Reuses the
    existing dashboard-notification idempotency (user, type, related_id), but
    keys related_id on this specific content hash so a repeat change fires a
    fresh alert while an unchanged page never repeats one."""
    from app.models.user import User
    from app.services.notification_service import create_notification
    from app.services.watch_service import find_watchers_for_company

    sent = 0
    for watch in find_watchers_for_company(db, company):
        user = db.get(User, watch.user_id)
        if user is None or not user.is_active:
            continue
        note = create_notification(
            db, user_id=user.id, to_email=user.email, type="link_updated",
            title=f"{company.company_name}'s careers page was updated",
            body=(f"The page you're watching for {company.company_name} "
                  f"({company.country}) looks like it changed. Take a look: {company.careers_url}"),
            related_type="company", related_id=f"{company.id}:{(company.content_hash or '')[:16]}",
            # A watch is an explicit "email me" opt-in, so it always emails --
            # unlike the broad new-jobs broadcast, this isn't gated behind the
            # platform-wide NOTIFY_EMAILS marketing toggle.
            send_email=True,
        )
        if note is not None:
            sent += 1
    return sent
