"""Notification creation and delivery (blueprint section 31).

Creates dashboard notifications (and optionally emails). Idempotent per
(user, type, related_id) so re-running matching or re-preparing an application
never spams the candidate with duplicates.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.notifications.email import get_email_provider

logger = logging.getLogger(__name__)


def _commit_closed(db: Session) -> None:
    """Commit and leave no transaction open. Roll back if the commit itself fails."""
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _rollback_if_open(db: Session) -> None:
    """A channel error must not leave this connection idle in a transaction."""
    try:
        if db.in_transaction():
            db.rollback()
    except Exception:
        logger.warning("Could not roll back after a notification send failure", exc_info=True)


def create_notification(db: Session, *, user_id: str, to_email: str | None, type: str,
                        title: str, body: str, related_type: str | None = None,
                        related_id: str | None = None, send_email: bool | None = None,
                        to_phone: str | None = None, link_url: str | None = None) -> Notification | None:
    # Idempotency: skip if a notification for the same trigger already exists.
    if related_id is not None:
        existing = (db.query(Notification)
                    .filter(Notification.user_id == user_id, Notification.type == type,
                            Notification.related_id == related_id)
                    .first())
        if existing:
            return None

    # Read anything the send step needs, then commit BEFORE SMTP/SMS/push.
    # Render free blocks outbound SMTP (Errno 101). The old code ran that send
    # inside the caller's transaction, so the SELECT stayed 'idle in transaction'
    # and the next deploy's ALTER TABLE waited on it until the boot was killed.
    push_tokens: list[str] = []
    if settings.NOTIFY_PUSH:
        from app.models.notification import PushToken
        push_tokens = [
            row.token for row in db.query(PushToken).filter(PushToken.user_id == user_id).all()
        ]

    note = Notification(user_id=user_id, type=type, title=title, body=body,
                        related_type=related_type, related_id=related_id, link_url=link_url)
    db.add(note)
    db.flush()
    note_id = note.id
    _commit_closed(db)

    should_email = settings.NOTIFY_EMAILS if send_email is None else send_email
    email_sent = False
    sms_sent = False
    push_sent = False

    if should_email and to_email:
        try:
            email_sent = bool(get_email_provider().send(to_email, title, body))
        except Exception:
            # Never let a channel failure break the flow -- but this used to be
            # completely silent, which matters a lot with NOTIFY_EMAILS on in
            # production: a candidate could simply never get a notification they
            # were relying on (e.g. "your application needs action") with nothing
            # anywhere recording that the send failed.
            logger.warning("Failed to email notification %r to user %s", type, user_id, exc_info=True)
            email_sent = False
            _rollback_if_open(db)

    if settings.NOTIFY_SMS and to_phone:
        try:
            from app.notifications.channels import get_sms_provider
            sms_sent = bool(get_sms_provider().send(to_phone, f"{title}: {body}"))
        except Exception:
            logger.warning("Failed to SMS notification %r to user %s", type, user_id, exc_info=True)
            sms_sent = False
            _rollback_if_open(db)

    if settings.NOTIFY_PUSH and push_tokens:
        try:
            from app.notifications.channels import get_push_provider
            provider = get_push_provider()
            push_sent = any(provider.send(token, title, body) for token in push_tokens)
        except Exception:
            logger.warning("Failed to push notification %r to user %s", type, user_id, exc_info=True)
            push_sent = False
            _rollback_if_open(db)

    if email_sent or sms_sent or push_sent:
        saved = db.get(Notification, note_id)
        if saved is not None:
            saved.email_sent = email_sent
            saved.sms_sent = sms_sent
            saved.push_sent = push_sent
            try:
                _commit_closed(db)
            except Exception:
                logger.warning(
                    "Notification %s was saved but the sent-flags could not be stored",
                    note_id, exc_info=True,
                )
                _rollback_if_open(db)
    # A trailing SELECT would leave the caller's connection in a transaction
    # again. Detach the row and roll that read back.
    loaded = db.get(Notification, note_id)
    if loaded is not None:
        db.expunge(loaded)
    _rollback_if_open(db)
    return loaded


def notify_strong_match(db, *, user, match, vacancy_title, company_name) -> Notification | None:
    return create_notification(
        db, user_id=user.id, to_email=user.email, type="strong_match",
        title=f"New strong job match found ({int(match.score)}%)",
        body=(f"{vacancy_title} at {company_name} — match {int(match.score)}% "
              f"({match.band}). Your tailored CV can be generated in one click."),
        related_type="match", related_id=match.id, to_phone=getattr(user, "mobile_number", None),
        send_email=None if _alerts_email_opted_in(user) else False,
    )


def notify_action_required(db, *, user, application, vacancy_title, company_name) -> Notification | None:
    return create_notification(
        db, user_id=user.id, to_email=user.email, type="action_required",
        title="Candidate action required",
        body=(f"Your application for {vacancy_title} at {company_name} is ready. "
              f"{application.action_required_note or 'Please review and submit.'}"),
        related_type="application", related_id=application.id, to_phone=getattr(user, "mobile_number", None),
    )


def notify_daily_agent_briefing(db, *, user, application_ids: list[str],
                                job_run_id: str | None = None) -> Notification | None:
    """Tell a candidate the Daily Agent drafted new ready-to-review applications
    for them — CV + cover letter generated, application queued in an
    awaiting-your-review state. Never implies anything was sent: the candidate
    still has to open each one and approve/submit it themselves.

    Idempotent per (user, job_run_id) when called from the scheduled job, same
    pattern as notify_new_jobs_broadcast — a re-run of the same job never
    re-notifies. Called with no job_run_id (e.g. an ad-hoc/manual run), it
    always sends, since there's no run to key idempotency on.
    """
    if not application_ids:
        return None
    from app.models.application import Application
    from app.models.company import Company
    from app.models.vacancy import Vacancy

    apps = db.query(Application).filter(Application.id.in_(application_ids)).all()
    if not apps:
        return None
    vacancies = {v.id: v for v in
                db.query(Vacancy).filter(Vacancy.id.in_({a.vacancy_id for a in apps})).all()}
    companies = {
        c.id: c.company_name
        for c in db.query(Company).filter(Company.id.in_({v.company_id for v in vacancies.values()})).all()
    }

    count = len(apps)
    named = [a for a in apps if a.vacancy_id in vacancies]
    highlights = ", ".join(
        f"{vacancies[a.vacancy_id].title} at {companies.get(vacancies[a.vacancy_id].company_id, 'a company')}"
        for a in named[:3]
    )
    if count > 3:
        highlights += f", and {count - 3} more"
    title = f"Your daily agent found {count} new application{'s' if count != 1 else ''} to review"
    body = (f"{highlights}. A tailored CV and cover letter were drafted for each one, and they're "
            f"queued ready to review — nothing is ever sent without you.")

    return create_notification(
        db, user_id=user.id, to_email=user.email, type="daily_agent_briefing",
        title=title, body=body, related_type="job_run", related_id=job_run_id,
        to_phone=getattr(user, "mobile_number", None),
        send_email=None if _alerts_email_opted_in(user) else False,
    )


def notify_new_jobs_broadcast(db, *, vacancy_ids: list[str], job_run_id: str) -> int:
    """Alert every active candidate that new vacancies were found in this scan run.

    Broad (non-personalised) alert, distinct from notify_strong_match: this fires
    for ANY newly discovered job, not just ones matching a candidate's profile.
    Idempotent per (user, job_run_id) — one notification per candidate per scan
    run, however many jobs it found, so re-running the same job never spams.
    """
    if not vacancy_ids:
        return 0
    from app.models.company import Company
    from app.models.user import User
    from app.models.vacancy import Vacancy

    vacancies = db.query(Vacancy).filter(Vacancy.id.in_(vacancy_ids)).all()
    if not vacancies:
        return 0
    companies = {
        c.id: c.company_name
        for c in db.query(Company).filter(Company.id.in_({v.company_id for v in vacancies})).all()
    }

    count = len(vacancies)
    highlights = ", ".join(f"{v.title} at {companies.get(v.company_id, 'a company')}" for v in vacancies[:3])
    if count > 3:
        highlights += f", and {count - 3} more"
    title = f"{count} new job{'s' if count != 1 else ''} just added"
    body = f"{highlights}. Head to Find Jobs to see them all."

    candidates = db.query(User).filter(User.role == "candidate", User.is_active.is_(True)).all()
    sent = 0
    for user in candidates:
        note = create_notification(
            db, user_id=user.id, to_email=user.email, type="new_jobs", title=title, body=body,
            related_type="job_run", related_id=job_run_id, to_phone=getattr(user, "mobile_number", None),
            send_email=None if _alerts_email_opted_in(user) else False,
        )
        if note is not None:
            sent += 1
    return sent


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


def _active_candidate(user) -> bool:
    """In-app tag notices stay inside the account. Consent is not required for that."""
    return bool(
        getattr(user, "role", None) == "candidate"
        and getattr(user, "is_active", False)
        and not getattr(user, "deleted_at", None)
    )


def _tagging_email_opted_in(user) -> bool:
    """Explicit tagging yes only. No recorded choice and an explicit no stay off."""
    return _active_candidate(user) and bool(
        getattr(user, "allow_tagging", False) and getattr(user, "allow_tagging_chosen_at", None)
    )


def _alerts_email_opted_in(user) -> bool:
    """Alert mail follows the alerts yes/no. A legacy True still counts as yes."""
    return bool(getattr(user, "notify_opportunity_alerts", False))


def _opening_for_link(db, link_url: str | None) -> tuple[str | None, str | None]:
    """Role title and employer name when this URL is already a stored listing."""
    if not link_url:
        return None, None
    from sqlalchemy import or_

    from app.models.company import Company
    from app.models.vacancy import Vacancy
    from app.scraper.urls import canonical_listing_url

    keys = {link_url}
    canonical = canonical_listing_url(link_url)
    if canonical:
        keys.add(canonical)
    row = (db.query(Vacancy.title, Company.company_name)
           .join(Company, Company.id == Vacancy.company_id)
           .filter(Vacancy.deleted_at.is_(None), Company.deleted_at.is_(None))
           .filter(or_(
               Vacancy.application_url.in_(keys),
               Vacancy.source_url.in_(keys),
               Vacancy.canonical_url.in_(keys),
           ))
           .first())
    if row is not None:
        return (row[0] or None), (row[1] or None)
    company = (db.query(Company.company_name)
               .filter(Company.deleted_at.is_(None), Company.careers_url.in_(keys))
               .first())
    if company is not None:
        return None, company[0]
    return None, None


def _suggestion_body(message: str, link_url: str | None,
                     role: str | None, employer: str | None) -> str:
    from datetime import datetime, timezone

    lines = [message.strip(), "", "Tagged by the Sospana Sonke team."]
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"Tagged at {when}.")
    if role:
        lines.append(f"Role: {role.strip()}")
    if employer:
        lines.append(f"Employer: {employer.strip()}")
    if link_url:
        lines.extend(["", link_url])
    return "\n".join(lines)


def notify_admin_suggestion(db, *, users: list, title: str, body: str,
                            link_url: str | None = None) -> tuple[int, int, int]:
    """In-app notice for every active candidate. Email only after an explicit yes.

    Returns ``(sent, duplicates, emailed)``. A missing choice and an explicit
    no both skip email. The same user and the same link is stored once.
    Email still follows ``NOTIFY_EMAILS`` and the Brevo or SMTP provider.
    """
    from app.notifications.links import validated_notice_url

    safe_link = validated_notice_url(link_url) if link_url else None
    role, employer = _opening_for_link(db, safe_link)
    notice_body = _suggestion_body(body, safe_link, role, employer)
    safe_title = " ".join(title.split())[:200] or "A listing for you"
    sent = 0
    duplicates = 0
    emailed = 0
    for user in users:
        if not _active_candidate(user):
            continue
        if safe_link:
            existing = (db.query(Notification)
                        .filter(Notification.user_id == user.id,
                                Notification.type == "admin_suggestion",
                                Notification.link_url == safe_link)
                        .first())
            if existing is not None:
                duplicates += 1
                continue
        mail = None if _tagging_email_opted_in(user) else False
        note = create_notification(
            db, user_id=user.id, to_email=user.email, type="admin_suggestion",
            title=safe_title, body=notice_body, link_url=safe_link,
            send_email=mail,
        )
        if note is not None:
            sent += 1
            if note.email_sent:
                emailed += 1
    return sent, duplicates, emailed


def notify_report_ready(db, *, user, report) -> Notification | None:
    return create_notification(
        db, user_id=user.id, to_email=user.email, type="report_ready",
        title="Your job-search report is ready",
        body="A new report summarising your matches and applications is available to download.",
        related_type="report", related_id=report.id, to_phone=getattr(user, "mobile_number", None),
    )
