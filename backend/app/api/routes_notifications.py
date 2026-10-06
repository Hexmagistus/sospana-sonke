"""Notification routes (candidate) and scheduler routes (admin) — blueprint Steps 11, 22, 31."""
import html
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.notification import Notification, JobRun, PushToken
from app.models.admin_ops import AdminAuditLog
from app.models.user import User
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.models.scan_log import ScanLog
from app.schemas.notification import (
    NotificationResponse, UnreadCountResponse, ScheduleResponse, ScheduleUpdateRequest, JobRunResponse,
    PushTokenRequest, PushTokenResponse, AdminSuggestionRequest, AdminSuggestionResponse,
    PreferenceEmailRequest, PreferenceEmailResponse, LoginDigestSettings, LoginDigestResult,
    SourceHealthResponse, SourceHealthItem, ScanLogItem, SourceActiveUpdate,
)
from app.scheduler.registry import get_schedule, set_schedule, JOBS
from app.scheduler.runner import run_job, UnknownJob
from app.services.notification_service import notify_admin_suggestion, RETIRED_TYPES
from app.services.preference_mail import send_preference_emails
from app.services.admin_login_alerts import send_login_digest

router = APIRouter(tags=["notifications"])


# ---- daily digest: one-click unsubscribe (linked from every digest email) ----

_PAGE = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
         "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
         "<meta name=\"robots\" content=\"noindex\"><title>Daily updates</title></head>"
         "<body style=\"font-family:system-ui,sans-serif;max-width:32rem;margin:3rem auto;padding:0 1rem\">"
         "{body}</body></html>")


def _unsub_user(db: Session, token: str) -> User | None:
    import jwt
    from app.core import security
    from app.services.daily_digest import UNSUBSCRIBE_TOKEN_TYPE
    try:
        payload = security.decode_token(token, UNSUBSCRIBE_TOKEN_TYPE)
    except jwt.PyJWTError:
        return None
    user = db.get(User, payload.get("sub"))
    return user if user is not None and user.deleted_at is None else None


@router.get("/notifications/digest/unsubscribe", response_class=HTMLResponse)
def digest_unsubscribe_page(token: str = Query(default="", max_length=2000), db: Session = Depends(get_db)):
    """A confirmation page. GET changes nothing, so mail scanners that prefetch links are harmless."""
    if _unsub_user(db, token) is None:
        return HTMLResponse(_PAGE.format(body="<h1>Link not valid</h1><p>This unsubscribe link is invalid or "
                                              "the account no longer exists. You can change your emails on the "
                                              "Preferences page after signing in.</p>"), status_code=400)
    action = html.escape(f"?token={token}", quote=True)
    return HTMLResponse(_PAGE.format(body=(
        "<h1>Stop the daily updates?</h1><p>You will no longer get the Your daily updates email. "
        "You can switch it back on any time on the Preferences page.</p>"
        f"<form method=\"post\" action=\"{action}\"><button type=\"submit\" "
        "style=\"padding:.6rem 1rem;font-size:1rem\">Unsubscribe</button></form>")))


@router.post("/notifications/digest/unsubscribe", response_class=HTMLResponse)
def digest_unsubscribe(token: str = Query(default="", max_length=2000), db: Session = Depends(get_db)):
    user = _unsub_user(db, token)
    if user is None:
        return HTMLResponse(_PAGE.format(body="<h1>Link not valid</h1>"), status_code=400)
    now = datetime.now(timezone.utc)
    user.digest_unsubscribed_at = now
    user.notify_opportunity_alerts = False
    user.notify_opportunity_alerts_chosen_at = now   # equal to the unsubscribe time: not a re-subscribe
    db.commit()
    return HTMLResponse(_PAGE.format(body="<h1>You are unsubscribed</h1><p>We will not send you the daily "
                                          "updates email again. You can change this any time on the "
                                          "Preferences page.</p>"))


# ---- candidate notifications ----

@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                       unread_only: bool = Query(default=False),
                       limit: int = Query(default=50, le=200)):
    q = db.query(Notification).filter(Notification.user_id == user.id,
                                      Notification.type.notin_(RETIRED_TYPES))
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    return [NotificationResponse.model_validate(n) for n in q.all()]


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = (db.query(func.count(Notification.id))
         .filter(Notification.user_id == user.id, Notification.is_read.is_(False),
                 Notification.type.notin_(RETIRED_TYPES)).scalar() or 0)
    return UnreadCountResponse(unread=n)


@router.post("/notifications/{note_id}/read", response_model=NotificationResponse)
def mark_read(note_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    note = db.get(Notification, note_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    note.is_read = True
    db.commit()
    db.refresh(note)
    return NotificationResponse.model_validate(note)


@router.post("/notifications/read-all", response_model=UnreadCountResponse)
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    (db.query(Notification)
     .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
     .update({Notification.is_read: True}))
    db.commit()
    return UnreadCountResponse(unread=0)


@router.post("/notifications/push-tokens", response_model=PushTokenResponse,
             status_code=status.HTTP_201_CREATED)
def register_push_token(body: PushTokenRequest, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    existing = (db.query(PushToken)
                .filter(PushToken.user_id == user.id, PushToken.token == body.token).first())
    if existing:
        existing.platform = body.platform
        db.commit()
        return PushTokenResponse(id=existing.id, platform=existing.platform)
    tok = PushToken(user_id=user.id, token=body.token, platform=body.platform)
    db.add(tok)
    db.commit()
    db.refresh(tok)
    return PushTokenResponse(id=tok.id, platform=tok.platform)


# ---- admin: suggest a post/link to relevant candidates ----

def _can_receive_in_app(user: User) -> bool:
    """A tag notice lives in the account. It does not require an email choice."""
    return bool(
        user.role == "candidate"
        and user.is_active
        and not user.deleted_at
    )


def _can_receive_broadcast(user: User) -> bool:
    """A send-to-everyone is not a personal tag. It stays with people who opted in."""
    return _can_receive_in_app(user) and bool(
        user.notify_opportunity_alerts or (
            user.allow_tagging and user.allow_tagging_chosen_at is not None
        )
    )


@router.post("/admin/suggestions", response_model=AdminSuggestionResponse)
def send_admin_suggestion(body: AdminSuggestionRequest, db: Session = Depends(get_db),
                          admin: User = Depends(require_admin)):
    if body.all_candidates:
        targets = db.query(User).filter(User.role == "candidate", User.is_active.is_(True)).all()
    elif body.user_ids:
        targets = (db.query(User)
                   .filter(User.id.in_(body.user_ids), User.is_active.is_(True))
                   .all())
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Provide user_ids or set all_candidates to true.")
    gate = _can_receive_broadcast if body.all_candidates else _can_receive_in_app
    eligible = [u for u in targets if gate(u)]
    skipped = len(targets) - len(eligible)
    sent, duplicates, emailed = (
        notify_admin_suggestion(db, users=eligible, title=body.title, body=body.body,
                                link_url=body.link_url)
        if eligible else (0, 0, 0)
    )
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action="notify",
        target_user_id=None,
        detail=(f"sent={sent} skipped={skipped} duplicates={duplicates} emailed={emailed} "
                f"link={1 if body.link_url else 0} title_len={len(body.title)}"),
    ))
    db.commit()
    return AdminSuggestionResponse(sent=sent, skipped=skipped, duplicates=duplicates, emailed=emailed)


@router.post("/admin/preference-email", response_model=PreferenceEmailResponse)
@limiter.limit("12/hour")
def send_preference_email(request: Request, body: PreferenceEmailRequest,
                          db: Session = Depends(get_db),
                          admin: User = Depends(require_admin)):
    """One-time service email to existing users who have not chosen their preferences.

    Admin only. dry_run is the default and only counts. A real send claims each
    address before the message leaves, stops at the daily cap, and never includes
    job content. The audit row stores counts, not addresses.
    """
    result = send_preference_emails(db, batch=body.batch, dry_run=body.dry_run)
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action="preference_email",
        target_user_id=None,
        detail=(f"dry_run={int(result['dry_run'])} eligible={result['eligible']} "
                f"sent={result['sent']} would_send={result['would_send']} "
                f"last_24h={result['sent_last_24h']}"),
    ))
    db.commit()
    return PreferenceEmailResponse(**result)


# ---- admin: client sign-in alerts ----

@router.get("/admin/login-alerts", response_model=LoginDigestSettings)
def get_login_alert_settings(admin: User = Depends(require_admin)):
    return LoginDigestSettings(email_digest=bool(admin.admin_login_digest))


@router.put("/admin/login-alerts", response_model=LoginDigestSettings)
@limiter.limit("30/hour")
def set_login_alert_settings(request: Request, body: LoginDigestSettings,
                             db: Session = Depends(get_db),
                             admin: User = Depends(require_admin)):
    """Turn this admin's optional email digest of client sign-ins on or off (default off)."""
    admin.admin_login_digest = bool(body.email_digest)
    if body.email_digest and admin.admin_login_digest_sent_at is None:
        from datetime import datetime, timezone
        # Start counting from now so switching it on does not mail a backlog.
        admin.admin_login_digest_sent_at = datetime.now(timezone.utc)
    db.commit()
    return LoginDigestSettings(email_digest=bool(admin.admin_login_digest))


@router.post("/admin/login-alerts/digest", response_model=LoginDigestResult)
@limiter.limit("6/hour")
def send_login_alert_digest(request: Request, db: Session = Depends(get_db),
                            admin: User = Depends(require_admin)):
    """Send this admin their pending digest now (only if they turned it on)."""
    result = send_login_digest(db, only_admin_id=admin.id)
    return LoginDigestResult(email_digest=bool(admin.admin_login_digest),
                             sent=result["sent"] > 0, clients=result["clients"])


# ---- admin scheduler ----

@router.get("/admin/source-health", response_model=SourceHealthResponse, dependencies=[Depends(require_admin)])
def source_health(db: Session = Depends(get_db)):
    """Last success, last error, and counts per careers source. Numbers only
    plus the 20 most recently checked sources — not the whole directory."""
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    week_start = now - timedelta(days=7)
    sources = db.query(func.count(VacancySource.id)).scalar() or 0
    employers = (db.query(func.count(Company.id)).filter(Company.deleted_at.is_(None)).scalar() or 0)
    open_vacancies = (db.query(func.count(Vacancy.id)).filter(Vacancy.is_open.is_(True)).scalar() or 0)
    expired = (db.query(func.count(Vacancy.id))
               .filter(Vacancy.lifecycle_status == "EXPIRED").scalar() or 0)
    new_today = (db.query(func.count(Vacancy.id))
                 .filter(Vacancy.first_seen_at >= today_start).scalar() or 0)
    new_week = (db.query(func.count(Vacancy.id))
                .filter(Vacancy.first_seen_at >= week_start).scalar() or 0)
    prevented = db.query(func.coalesce(func.sum(VacancySource.duplicates_prevented), 0)).scalar() or 0
    review_states = (
        "REQUIRES_REVIEW", "INVALID_URL", "SITE_CHANGED", "JAVASCRIPT_REQUIRED",
        "BLOCKED", "PARSER_ERROR", "NEEDS_REVIEW",
    )
    needs_review = (db.query(func.count(VacancySource.id))
                    .filter(VacancySource.scraper_status.in_(review_states)).scalar() or 0)
    last_success_at = (db.query(func.max(VacancySource.last_checked))
                       .filter(VacancySource.last_status == "ok").scalar())
    by_status = {row[0] or "unknown": row[1] for row in
                 db.query(VacancySource.last_status, func.count(VacancySource.id))
                 .group_by(VacancySource.last_status).all()}
    by_scraper = {row[0] or "unknown": row[1] for row in
                  db.query(VacancySource.scraper_status, func.count(VacancySource.id))
                  .group_by(VacancySource.scraper_status).all()}
    by_ats = {row[0] or "unknown": row[1] for row in
              db.query(VacancySource.ats_type, func.count(VacancySource.id))
              .group_by(VacancySource.ats_type).all()}
    recent_rows = (db.query(VacancySource, Company.company_name, Company.country, Company.id)
                   .join(Company, Company.id == VacancySource.company_id)
                   .order_by(VacancySource.last_checked.is_(None), VacancySource.last_checked.desc())
                   .limit(20).all())
    recent = [SourceHealthItem(
        source_id=src.id, company_id=company_id, company_name=name, country=country,
        ats_type=src.ats_type, url=src.url, active=bool(src.active),
        last_status=src.last_status, scraper_status=src.scraper_status,
        last_error=src.last_error, last_checked=src.last_checked,
        last_vacancy_count=src.last_vacancy_count, consecutive_failures=src.consecutive_failures or 0,
    ) for src, name, country, company_id in recent_rows]
    return SourceHealthResponse(
        sources=sources, employers=employers, open_vacancies=open_vacancies,
        expired_vacancies=expired, vacancies_new_today=new_today, vacancies_new_week=new_week,
        duplicates_prevented=int(prevented), needs_review=needs_review,
        last_success_at=last_success_at, by_status=by_status, by_scraper_status=by_scraper,
        by_ats=by_ats, recent=recent,
    )


@router.get("/admin/scan-logs", response_model=list[ScanLogItem], dependencies=[Depends(require_admin)])
def list_scan_logs(db: Session = Depends(get_db),
                   status_filter: str | None = Query(default=None, alias="status"),
                   company_id: str | None = Query(default=None),
                   limit: int = Query(default=50, le=100)):
    """Recent scan attempts. No candidate or admin identity is stored on these rows."""
    q = (db.query(ScanLog, Company.company_name)
         .outerjoin(Company, Company.id == ScanLog.company_id)
         .filter(ScanLog.deleted_at.is_(None)))
    if status_filter:
        q = q.filter(ScanLog.status == status_filter)
    if company_id:
        q = q.filter(ScanLog.company_id == company_id)
    rows = q.order_by(ScanLog.finished_at.is_(None), ScanLog.finished_at.desc()).limit(limit).all()
    return [ScanLogItem(
        id=log.id, company_id=log.company_id, company_name=name, url=log.url,
        status=log.status, error_category=log.error_category, pages_scanned=log.pages_scanned or 0,
        vacancies_discovered=log.vacancies_discovered or 0, vacancies_new=log.vacancies_new or 0,
        vacancies_updated=log.vacancies_updated or 0,
        duplicates_prevented=log.duplicates_prevented or 0,
        vacancies_closed=log.vacancies_closed or 0, duration_ms=log.duration_ms,
        parser_used=log.parser_used, finished_at=log.finished_at,
    ) for log, name in rows]


@router.post("/admin/sources/{source_id}/active")
def set_source_active(source_id: str, body: SourceActiveUpdate, db: Session = Depends(get_db),
                      admin: User = Depends(require_admin)):
    """Pause or resume one careers source. Does not delete vacancies."""
    source = db.get(VacancySource, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    source.active = body.active
    if not body.active:
        source.scraper_status = "DISABLED"
    elif source.scraper_status == "DISABLED":
        source.scraper_status = None
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action="source_resume" if body.active else "source_pause",
        target_user_id=None,
        detail=f"source={source_id} company={source.company_id}",
    ))
    db.commit()
    return {"source_id": source.id, "active": source.active}

@router.get("/admin/schedule", response_model=ScheduleResponse, dependencies=[Depends(require_admin)])
def read_schedule(db: Session = Depends(get_db)):
    return ScheduleResponse(schedule=get_schedule(db))


@router.put("/admin/schedule", response_model=ScheduleResponse, dependencies=[Depends(require_admin)])
def update_schedule(body: ScheduleUpdateRequest, db: Session = Depends(get_db)):
    return ScheduleResponse(schedule=set_schedule(db, body.schedule))


@router.post("/admin/jobs/{name}/run", response_model=JobRunResponse, dependencies=[Depends(require_admin)])
def trigger_job(name: str, db: Session = Depends(get_db)):
    try:
        return JobRunResponse.model_validate(run_job(db, name))
    except UnknownJob:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Unknown job '{name}'. Known jobs: {', '.join(JOBS)}.")


@router.get("/admin/jobs/runs", response_model=list[JobRunResponse], dependencies=[Depends(require_admin)])
def list_job_runs(db: Session = Depends(get_db), limit: int = Query(default=50, le=200)):
    rows = db.query(JobRun).order_by(JobRun.started_at.desc()).limit(limit).all()
    return [JobRunResponse.model_validate(r) for r in rows]
