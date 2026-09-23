"""Owner alert: email the platform owner every time someone signs in.

Recipient is LOGIN_ALERT_EMAIL (comma-separated allowed), falling back to
SMTP_USER (the Gmail inbox that sends the platform's mail), then ADMIN_EMAIL. Independent of NOTIFY_EMAILS (that toggle is for candidate-facing
mail). Runs as a FastAPI background task so SMTP never slows down the login
response, and never raises — a failed alert must not break sign-in.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.core.client_ip import client_ip
from app.core.config import settings

logger = logging.getLogger(__name__)

SAST = timezone(timedelta(hours=2), "SAST")


def alert_recipients() -> list[str]:
    if not settings.LOGIN_ALERTS_ENABLED:
        return []
    raw = settings.LOGIN_ALERT_EMAIL or settings.SMTP_USER or settings.ADMIN_EMAIL or ""
    return [e.strip() for e in raw.split(",") if e.strip()]




def build_login_alert(*, first_name: str, last_name: str, email: str, role: str,
                      method: str, ip: str, user_agent: str, new_account: bool = False,
                      when: datetime | None = None) -> tuple[str, str]:
    when = (when or datetime.now(timezone.utc)).astimezone(SAST)
    name = f"{first_name} {last_name}".strip()
    tag = " (NEW account)" if new_account else ""
    subject = f"🔔 {settings.APP_NAME} login: {name}{tag}"
    body = (
        f"Someone just signed in to {settings.APP_NAME}.\n\n"
        f"Name:    {name}\n"
        f"Email:   {email}\n"
        f"Role:    {role}\n"
        f"Method:  {method}{' — first sign-in, account created' if new_account else ''}\n"
        f"Time:    {when:%a %d %b %Y, %H:%M:%S} SAST\n"
        f"IP:      {ip}\n"
        f"Device:  {user_agent or 'unknown'}\n"
    )
    return subject, body


def send_login_alert(subject: str, body: str) -> None:
    recipients = alert_recipients()
    if not recipients:
        return
    try:
        from app.notifications.email import get_email_provider
        provider = get_email_provider()
        for to in recipients:
            provider.send(to, subject, body)
    except Exception:
        logger.error("Failed to send login alert", exc_info=True)


def queue_login_alert(background_tasks, request, user, *, method: str, new_account: bool = False) -> None:
    """Build the alert from the request now; send it after the response goes out."""
    if not alert_recipients():
        return
    subject, body = build_login_alert(
        first_name=user.first_name, last_name=user.last_name, email=user.email,
        role=user.role, method=method, ip=client_ip(request),
        user_agent=request.headers.get("user-agent", ""), new_account=new_account,
    )
    background_tasks.add_task(send_login_alert, subject, body)
