"""One-time service email asking existing users to choose their preferences.

This is a service notice, not an advertisement and not a job alert. It names
Sospana Sonke, explains why the person is getting it (POPIA), says nothing
changes until they choose, and links to the preferences page. It carries no
job, vacancy, salary or employer content.

Safety rules, all enforced here and covered by tests:

* Admin-triggered only (the route requires an admin); nothing sends it on a timer.
* Only active candidate accounts that still have at least one preference
  "not chosen" are eligible, and only if they have a usable email address.
* Each address is *claimed* (``consent_prompt_sent_at`` set with a conditional
  UPDATE) before the message leaves, so two clicks or a retry can never send a
  second copy. A failed send releases that claim so the next day can retry it.
* Brevo's free plan allows 300 emails a day. The campaign stops at
  ``PREFERENCE_EMAIL_DAILY_CAP`` (250, leaving room for password-reset and
  verification mail) counted over a rolling 24 hours that also includes
  notification mail already sent. The rest resumes automatically once that
  window frees up, so the admin simply presses the button again.
* Each request sends at most ``MAX_BATCH`` messages.
* Order inside the queue: South Africa first, then the rest of SADC, then
  the rest of Africa, then other regions (by the profile country), oldest
  account first within a band.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.models.profile import CandidateProfile
from app.models.user import User
from app.notifications.email import get_email_provider

logger = logging.getLogger(__name__)

BREVO_FREE_DAILY_LIMIT = 300
PREFERENCE_EMAIL_DAILY_CAP = 250
PREFERENCE_EMAIL_DEFAULT_BATCH = 40
MAX_BATCH = 50
WINDOW = timedelta(hours=24)

_SUBJECT = "Sospana Sonke: please choose your account preferences"
# Words that must never appear in this message (no job content).
_FORBIDDEN = ("job", "vacanc", "career", "hiring", "apply", "opportunit", "salary", "marketing")


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
    return f"{public_app_url()}/preferences"


def privacy_url() -> str:
    return f"{public_app_url()}/privacy"


def service_email_body(user: User | None = None) -> str:
    """The whole message. Plain text; a URL on its own line becomes a button."""
    first = (getattr(user, "first_name", "") or "").strip()
    greeting = f"Hello {first}," if first else "Hello,"
    return (
        f"{greeting}\n"
        "\n"
        "You have an account with Sospana Sonke. This is a short service notice "
        "about your account settings. It is not an advertisement.\n"
        "\n"
        "Please choose three preferences. Each one is separate, and nothing is "
        "switched on until you choose:\n"
        "1. Whether an administrator may tag you to employers.\n"
        "2. The kind of post you want to be considered for.\n"
        "3. Whether you want alerts about matching posts.\n"
        "\n"
        "Choose here (you can change any of them later):\n"
        f"{preferences_url()}\n"
        "\n"
        "Why you are receiving this: you hold a Sospana Sonke account, and the "
        "Protection of Personal Information Act (POPIA) says we must ask you "
        "before we use your information in these ways. Until you choose, we will "
        "not tag you to employers or send you alerts.\n"
        "\n"
        "This is a one-time message and we will not send it again. To stop any "
        "optional email from us, choose No on the preferences page, or delete "
        "your account from the Security page. To use your POPIA rights, contact "
        "our Information Officer, named in the Privacy Policy:\n"
        f"{privacy_url()}"
    )


def _assert_clean(body: str) -> None:
    low = body.lower()
    if any(word in low for word in _FORBIDDEN):
        raise RuntimeError("service email contains wording that must stay out of this message")


def _needs_choice():
    return or_(
        and_(User.allow_tagging_chosen_at.is_(None), User.allow_tagging.is_(False)),
        User.preferred_post_chosen_at.is_(None),
        and_(User.notify_opportunity_alerts_chosen_at.is_(None),
             User.notify_opportunity_alerts.is_(False)),
    )


def _has_email():
    # NOT NULL in the model, but old or imported rows can hold "" or a stub.
    return and_(User.email.isnot(None), func.length(func.trim(User.email)) > 3,
                User.email.like("%@%"))


def _eligible_filter():
    return and_(
        User.role == "candidate",
        User.is_active.is_(True),
        User.deleted_at.is_(None),
        User.consent_prompt_sent_at.is_(None),
        _has_email(),
        _needs_choice(),
    )


def _window_start(now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)) - WINDOW


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def preference_email_counts(db: Session, *, batch: int, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    start = _window_start(now)
    eligible = db.query(func.count(User.id)).filter(_eligible_filter()).scalar() or 0
    skipped_no_email = (db.query(func.count(User.id))
                        .filter(User.role == "candidate", User.is_active.is_(True),
                                User.deleted_at.is_(None),
                                User.consent_prompt_sent_at.is_(None),
                                _needs_choice(), ~_has_email())
                        .scalar() or 0)
    already_sent = (db.query(func.count(User.id))
                    .filter(User.consent_prompt_sent_at.isnot(None)).scalar() or 0)
    campaign_24h = (db.query(func.count(User.id))
                    .filter(User.consent_prompt_sent_at.isnot(None),
                            User.consent_prompt_sent_at >= start).scalar() or 0)
    other_24h = (db.query(func.count(Notification.id))
                 .filter(Notification.email_sent.is_(True),
                         Notification.created_at >= start).scalar() or 0)
    used = int(campaign_24h) + int(other_24h)
    remaining = max(0, PREFERENCE_EMAIL_DAILY_CAP - used)
    batch = max(0, min(int(batch), MAX_BATCH))
    would = min(batch, remaining, int(eligible))
    resume_at = None
    if remaining == 0 and eligible:
        oldest = (db.query(func.min(User.consent_prompt_sent_at))
                  .filter(User.consent_prompt_sent_at >= start).scalar())
        if oldest is not None:
            resume_at = (_aware(oldest) + WINDOW).isoformat()
    return {
        "eligible": int(eligible),
        "skipped_no_email": int(skipped_no_email),
        "already_sent": int(already_sent),
        "sent_last_24h": used,
        "remaining_today": remaining,
        "daily_cap": PREFERENCE_EMAIL_DAILY_CAP,
        "provider_daily_limit": BREVO_FREE_DAILY_LIMIT,
        "batch": batch,
        "would_send": would,
        "resume_at": resume_at,
    }


def _next_batch_ids(db: Session, n: int) -> list[str]:
    """Queue order: South Africa, rest of SADC, rest of Africa, then elsewhere."""
    from app.services.scan_runner import country_band

    rows = (db.query(User.id, User.created_at, CandidateProfile.country)
            .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
            .filter(_eligible_filter())
            .all())
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    rows.sort(key=lambda r: (country_band(r[2]),
                             _aware(r[1]) if r[1] else epoch,
                             r[0]))
    return [r[0] for r in rows[:n]]


def send_preference_emails(db: Session, *, batch: int, dry_run: bool) -> dict:
    """Count (dry run) or send one batch. Claim first, send second, release failures."""
    counts = preference_email_counts(db, batch=batch)
    counts["dry_run"] = dry_run
    counts["sent"] = 0
    counts["failed"] = 0
    if dry_run or counts["would_send"] <= 0:
        return counts

    ids = _next_batch_ids(db, counts["would_send"])
    now = datetime.now(timezone.utc)
    claimed: list[tuple[str, str, str]] = []
    for user_id in ids:
        # Conditional claim: if another request got there first, rowcount is 0.
        result = db.execute(
            update(User)
            .where(User.id == user_id, User.consent_prompt_sent_at.is_(None))
            .values(consent_prompt_sent_at=now)
        )
        if result.rowcount != 1:
            continue
        row = db.get(User, user_id)
        body = service_email_body(row)
        _assert_clean(body)
        claimed.append((user_id, row.email, body))
    db.commit()

    provider = get_email_provider()
    sent_ids: list[str] = []
    for user_id, email, body in claimed:
        try:
            ok = bool(provider.send(email, _SUBJECT, body))
        except Exception:
            logger.warning("Preference service email failed", exc_info=True)
            ok = False
        if not ok:
            break  # the provider is down or out of quota: stop, do not hammer it
        sent_ids.append(user_id)

    unsent = [user_id for user_id, _e, _b in claimed if user_id not in set(sent_ids)]
    if unsent:
        db.execute(update(User).where(User.id.in_(unsent)).values(consent_prompt_sent_at=None))
        db.commit()
        logger.warning("Preference email batch stopped after %s sent; %s left for later",
                       len(sent_ids), len(unsent))

    after = preference_email_counts(db, batch=batch)
    after["dry_run"] = False
    after["sent"] = len(sent_ids)
    after["failed"] = len(unsent)
    return after


def ensure_consent_notice(db: Session, user: User) -> None:
    """One in-app notice per account while a preference is unchosen. No email."""
    if user is None or user.role != "candidate" or not user.is_active or user.deleted_at is not None:
        return
    if not user.consent_pending:
        return
    from app.services.notification_service import create_notification

    create_notification(
        db, user_id=user.id, to_email=user.email, type="consent_choices",
        title="Please choose your preferences",
        body=("Choose whether an administrator may tag you to employers, the kind of "
              "post you want to be considered for, and whether you want alerts. "
              "Nothing is switched on until you choose."),
        link_url="/preferences", related_id="consent-choices", send_email=False,
    )
