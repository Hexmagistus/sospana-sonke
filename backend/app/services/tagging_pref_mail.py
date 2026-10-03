"""One service email for accounts that have never chosen tagging email.

This is not a job alert. It names Sospana Sonke, says a notice can sit inside
the account, and links to the preferences page so the person can turn email
on or leave it off. Each address is stamped before the send, so a retry does
not send a second copy. The Brevo free plan allows 300 messages a day: this
stops when that many have been stamped today (UTC) and continues the next day.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.notifications.email import get_email_provider

logger = logging.getLogger(__name__)

TAGGING_PREF_DAILY_CAP = 300
TAGGING_PREF_DEFAULT_BATCH = 40
_SUBJECT = "Sospana Sonke: choose how we contact you"
_FORBIDDEN = ("job", "vacancy", "career", "hiring", "apply", "opportunity", "salary", "marketing")


def public_app_url() -> str:
    raw = (getattr(settings, "PUBLIC_APP_URL", None) or "").strip()
    if raw:
        return raw.rstrip("/")
    for origin in (settings.CORS_ORIGINS or "").split(","):
        origin = origin.strip().rstrip("/")
        if origin.startswith("http://") or origin.startswith("https://"):
            return origin
    return "http://localhost:3000"


def preferences_url() -> str:
    return f"{public_app_url()}/security#notification-preferences"


def _label(state: str) -> str:
    if state == "yes":
        return "Yes"
    if state == "no":
        return "No"
    return "Not chosen"


def service_email_body(user: User | None = None) -> str:
    """One settings message. States come from the account. No listing content."""
    tagging = _label(user.tagging_state) if user is not None else "Not chosen"
    post = _label(user.contact_by_post_state) if user is not None else "Not chosen"
    alerts = _label(user.alerts_state) if user is not None else "Not chosen"
    url = preferences_url()
    return (
        "Sospana Sonke\n"
        "\n"
        "You have an account with us. Please choose the three options below. "
        "Each one is separate.\n"
        "\n"
        f"Tagging: {tagging}\n"
        f"Preferred post: {post}\n"
        f"Alerts: {alerts}\n"
        "\n"
        "Tagging means an administrator may tag you. "
        "Preferred post means we may contact you by post. "
        "Alerts means we may write to you about a match.\n"
        "\n"
        "Choose or turn off:\n"
        f"{url}\n"
        "\n"
        "This is one message about your settings. It is not an advertisement, "
        "and we will not send it again."
    )


def _assert_clean(body: str) -> None:
    low = body.lower()
    if any(word in low for word in _FORBIDDEN):
        raise RuntimeError("service email contains wording that must stay out of this message")


def _utc_day_start(now: datetime | None = None) -> datetime:
    moment = now or datetime.now(timezone.utc)
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def _needs_choice():
    from sqlalchemy import and_, or_
    return or_(
        and_(User.allow_tagging_chosen_at.is_(None), User.allow_tagging.is_(False)),
        and_(User.contact_by_post_chosen_at.is_(None), User.contact_by_post.is_(False)),
        and_(User.notify_opportunity_alerts_chosen_at.is_(None),
             User.notify_opportunity_alerts.is_(False)),
    )


def _eligible(db: Session):
    return (db.query(User)
            .filter(User.role == "candidate",
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                    User.consent_prompt_sent_at.is_(None),
                    _needs_choice()))


def tagging_pref_counts(db: Session, *, batch: int, now: datetime | None = None) -> dict:
    start = _utc_day_start(now)
    eligible = _eligible(db).count()
    already_sent = (db.query(func.count(User.id))
                    .filter(User.consent_prompt_sent_at.isnot(None))
                    .scalar() or 0)
    sent_today = (db.query(func.count(User.id))
                  .filter(User.consent_prompt_sent_at.isnot(None),
                          User.consent_prompt_sent_at >= start)
                  .scalar() or 0)
    remaining = max(0, TAGGING_PREF_DAILY_CAP - int(sent_today))
    would = min(max(batch, 0), remaining, int(eligible))
    resume = None
    if remaining == 0 and eligible:
        resume = (start + timedelta(days=1)).date().isoformat()
    return {
        "eligible": int(eligible),
        "already_sent": int(already_sent),
        "sent_today": int(sent_today),
        "remaining_today": remaining,
        "daily_cap": TAGGING_PREF_DAILY_CAP,
        "batch": batch,
        "would_send": would,
        "resume_on": resume,
    }


def send_tagging_preference_emails(db: Session, *, batch: int, dry_run: bool) -> dict:
    """Stamp, then send. A failed send clears that stamp so tomorrow can retry it.

    People who were stamped stay stamped even if this process stops afterwards,
    so they are not mailed twice.
    """
    counts = tagging_pref_counts(db, batch=batch)
    counts["dry_run"] = dry_run
    counts["sent"] = 0
    if dry_run or counts["would_send"] <= 0:
        return counts

    rows = (_eligible(db)
            .order_by(User.created_at.asc(), User.id.asc())
            .limit(counts["would_send"])
            .all())
    now = datetime.now(timezone.utc)
    claimed = []
    for row in rows:
        body = service_email_body(row)
        _assert_clean(body)
        claimed.append((row.id, row.email, body))
        row.consent_prompt_sent_at = now
    db.commit()

    provider = get_email_provider()
    sent_ids: list[str] = []
    failed_id: str | None = None
    for user_id, email, body in claimed:
        try:
            ok = bool(provider.send(email, _SUBJECT, body))
        except Exception:
            logger.warning("Tagging-preference service email failed", exc_info=True)
            ok = False
        if not ok:
            failed_id = user_id
            break
        sent_ids.append(user_id)

    unsent = [user_id for user_id, _email, _body in claimed if user_id not in sent_ids]
    if unsent:
        (db.query(User)
         .filter(User.id.in_(unsent))
         .update({User.consent_prompt_sent_at: None}, synchronize_session=False))
        db.commit()
        if failed_id is not None:
            logger.warning(
                "Tagging-preference batch stopped after %s sent; %s left for a later day",
                len(sent_ids), len(unsent),
            )

    counts = tagging_pref_counts(db, batch=batch)
    counts["dry_run"] = False
    counts["sent"] = len(sent_ids)
    return counts


def ensure_consent_notice(db: Session, user: User) -> None:
    """One in-app notice listing the three choices. No email."""
    if user is None or user.role != "candidate" or not user.is_active or user.deleted_at is not None:
        return
    if not user.consent_pending:
        return
    from app.services.notification_service import create_notification

    body = service_email_body(user)
    _assert_clean(body)
    create_notification(
        db, user_id=user.id, to_email=user.email, type="consent_choices",
        title=_SUBJECT, body=body, link_url=preferences_url(),
        related_id="consent-choices", send_email=False,
    )
