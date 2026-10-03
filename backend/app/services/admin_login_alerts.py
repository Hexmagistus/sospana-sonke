"""Admin sign-in alerts for client logins.

When a client (candidate) signs in, every active admin gets an in-app notice
(type ``client_login``) that links to the Admin page. The client gets nothing
and no email goes out per sign-in. An admin can opt in to a daily email digest
of those sign-ins; that is off by default and is the admin's own setting.

Admin sign-ins do not create notices. One notice per admin per client per
UTC day keeps a busy day from burying the bell.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)

SAST = timezone(timedelta(hours=2), "SAST")
CLIENT_LOGIN_TYPE = "client_login"
ADMIN_LINK = "/admin"
# The job path will not mail the same admin more often than this.
DIGEST_MIN_INTERVAL = timedelta(hours=12)
DIGEST_MAX_LINES = 50


def _day_key(user_id: str, new_account: bool, now: datetime) -> str:
    raw = f"{user_id}:{now:%Y-%m-%d}:{'new' if new_account else 'login'}"
    return hashlib.sha1(raw.encode()).hexdigest()[:32]  # fits Notification.related_id (36)


def notify_admins_of_client_login(db: Session, user: User, *, method: str,
                                  new_account: bool = False) -> int:
    """In-app notice to each active admin. Never raises: sign-in must not fail on this."""
    try:
        if user.role != "candidate":
            return 0
        name = f"{user.first_name} {user.last_name}".strip() or "A client"
        user_id = user.id
        now = datetime.now(timezone.utc)
        when = now.astimezone(SAST)
        title = f"{'New client signed in' if new_account else 'Client signed in'}: {name}"[:200]
        body = (f"{name} signed in with {method} at {when:%a %d %b %Y, %H:%M} SAST.\n"
                "Open the Admin page to see their account.")
        admins = (db.query(User.id, User.email)
                  .filter(User.role == "admin", User.is_active.is_(True),
                          User.deleted_at.is_(None)).all())
        key = _day_key(user_id, new_account, now)
        from app.services.notification_service import create_notification
        made = 0
        for admin_id, admin_email in admins:
            note = create_notification(
                db, user_id=admin_id, to_email=admin_email, type=CLIENT_LOGIN_TYPE,
                title=title, body=body, related_type="user", related_id=key,
                link_url=ADMIN_LINK, send_email=False,
            )
            if note is not None:
                made += 1
        return made
    except Exception:
        logger.warning("Could not store the admin sign-in notice", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return 0


def _digest_body(notes: list[Notification]) -> str:
    lines = [f"{settings.APP_NAME}: client sign-ins since your last digest.", ""]
    for n in notes[:DIGEST_MAX_LINES]:
        created = n.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        lines.append(f"- {n.title.split(': ', 1)[-1]} at {created.astimezone(SAST):%d %b %H:%M} SAST")
    if len(notes) > DIGEST_MAX_LINES:
        lines.append(f"...and {len(notes) - DIGEST_MAX_LINES} more.")
    lines += ["", "This digest is optional and you can switch it off on the Admin page."]
    return "\n".join(lines)


def send_login_digest(db: Session, *, only_admin_id: str | None = None,
                      respect_interval: bool = False) -> dict:
    """Email each opted-in admin the client sign-ins since their last digest."""
    from app.notifications.email import get_email_provider

    q = db.query(User).filter(User.role == "admin", User.is_active.is_(True),
                              User.deleted_at.is_(None), User.admin_login_digest.is_(True))
    if only_admin_id:
        q = q.filter(User.id == only_admin_id)
    now = datetime.now(timezone.utc)
    sent = 0
    clients = 0
    for admin in q.all():
        last = admin.admin_login_digest_sent_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if respect_interval and last is not None and now - last < DIGEST_MIN_INTERVAL:
            continue
        since = last or (now - timedelta(hours=24))
        notes = (db.query(Notification)
                 .filter(Notification.user_id == admin.id,
                         Notification.type == CLIENT_LOGIN_TYPE,
                         Notification.created_at > since)
                 .order_by(Notification.created_at.asc()).all())
        if not notes:
            continue
        email, count, body = admin.email, len(notes), _digest_body(notes)
        admin_id = admin.id
        subject = f"{settings.APP_NAME}: {count} client sign-in{'s' if count != 1 else ''}"
        try:
            ok = bool(get_email_provider().send(email, subject, body))
        except Exception:
            logger.warning("Admin sign-in digest failed", exc_info=True)
            ok = False
        if ok:
            row = db.get(User, admin_id)
            row.admin_login_digest_sent_at = now
            db.commit()
            sent += 1
            clients += count
    return {"sent": sent, "clients": clients}
