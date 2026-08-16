"""Notification creation and delivery (blueprint section 31).

Creates dashboard notifications (and optionally emails). Idempotent per
(user, type, related_id) so re-running matching or re-preparing an application
never spams the candidate with duplicates.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.notifications.email import get_email_provider


def create_notification(db: Session, *, user_id: str, to_email: str | None, type: str,
                        title: str, body: str, related_type: str | None = None,
                        related_id: str | None = None, send_email: bool | None = None,
                        to_phone: str | None = None) -> Notification | None:
    # Idempotency: skip if a notification for the same trigger already exists.
    if related_id is not None:
        existing = (db.query(Notification)
                    .filter(Notification.user_id == user_id, Notification.type == type,
                            Notification.related_id == related_id)
                    .first())
        if existing:
            return None

    note = Notification(user_id=user_id, type=type, title=title, body=body,
                        related_type=related_type, related_id=related_id)

    should_email = settings.NOTIFY_EMAILS if send_email is None else send_email
    if should_email and to_email:
        try:
            note.email_sent = get_email_provider().send(to_email, title, body)
        except Exception:
            note.email_sent = False  # never let a channel failure break the flow

    if settings.NOTIFY_SMS and to_phone:
        try:
            from app.notifications.channels import get_sms_provider
            note.sms_sent = get_sms_provider().send(to_phone, f"{title}: {body}")
        except Exception:
            note.sms_sent = False

    if settings.NOTIFY_PUSH:
        try:
            from app.notifications.channels import get_push_provider
            from app.models.notification import PushToken
            provider = get_push_provider()
            tokens = db.query(PushToken).filter(PushToken.user_id == user_id).all()
            note.push_sent = any(provider.send(t.token, title, body) for t in tokens)
        except Exception:
            note.push_sent = False

    db.add(note)
    db.flush()
    return note


def notify_strong_match(db, *, user, match, vacancy_title, company_name) -> Notification | None:
    return create_notification(
        db, user_id=user.id, to_email=user.email, type="strong_match",
        title=f"New strong job match found ({int(match.score)}%)",
        body=(f"{vacancy_title} at {company_name} — match {int(match.score)}% "
              f"({match.band}). Your tailored CV can be generated in one click."),
        related_type="match", related_id=match.id, to_phone=getattr(user, "mobile_number", None),
    )


def notify_action_required(db, *, user, application, vacancy_title, company_name) -> Notification | None:
    return create_notification(
        db, user_id=user.id, to_email=user.email, type="action_required",
        title="Candidate action required",
        body=(f"Your application for {vacancy_title} at {company_name} is ready. "
              f"{application.action_required_note or 'Please review and submit.'}"),
        related_type="application", related_id=application.id, to_phone=getattr(user, "mobile_number", None),
    )


def notify_admins(db, *, type: str, title: str, body: str,
                  related_type: str | None = None, related_id: str | None = None) -> int:
    """Send a dashboard notification to every active administrator (blueprint section 23)."""
    from app.models.user import User
    admins = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).all()
    sent = 0
    for admin in admins:
        note = create_notification(db, user_id=admin.id, to_email=admin.email, type=type,
                                   title=title, body=body, related_type=related_type,
                                   related_id=None, send_email=False)
        # related_id kept None so repeated breakage episodes each alert (edge-triggered upstream).
        if note is not None:
            sent += 1
    return sent


def notify_report_ready(db, *, user, report) -> Notification | None:
    return create_notification(
        db, user_id=user.id, to_email=user.email, type="report_ready",
        title="Your job-search report is ready",
        body="A new report summarising your matches and applications is available to download.",
        related_type="report", related_id=report.id, to_phone=getattr(user, "mobile_number", None),
    )
