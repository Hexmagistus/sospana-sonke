"""Notification routes (candidate) and scheduler routes (admin) — blueprint Steps 11, 22, 31."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
    TaggingPrefEmailRequest, TaggingPrefEmailResponse,
    SourceHealthResponse, SourceHealthItem, ScanLogItem, SourceActiveUpdate,
)
from app.scheduler.registry import get_schedule, set_schedule, JOBS
from app.scheduler.runner import run_job, UnknownJob
from app.services.notification_service import notify_admin_suggestion
from app.services.tagging_pref_mail import send_tagging_preference_emails

router = APIRouter(tags=["notifications"])


# ---- candidate notifications ----

@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                       unread_only: bool = Query(default=False),
                       limit: int = Query(default=50, le=200)):
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    return [NotificationResponse.model_validate(n) for n in q.all()]


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = (db.query(func.count(Notification.id))
         .filter(Notification.user_id == user.id, Notification.is_read.is_(False)).scalar() or 0)
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
        user.notify_opportunity_alerts or user.tagging_email is True
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


@router.post("/admin/tagging-preference-email", response_model=TaggingPrefEmailResponse)
@limiter.limit("6/hour")
def send_tagging_preference_email(request: Request, body: TaggingPrefEmailRequest,
                                  db: Session = Depends(get_db),
                                  admin: User = Depends(require_admin)):
    """One service email for accounts that have never chosen tagging email.

    dry_run is the default and only counts. A real send stamps each address
    before the message leaves, stops at the daily cap, and never includes a
    listing. The audit row stores counts, not addresses.
    """
    result = send_tagging_preference_emails(db, batch=body.batch, dry_run=body.dry_run)
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action="tagging_pref_email",
        target_user_id=None,
        detail=(f"dry_run={int(result['dry_run'])} eligible={result['eligible']} "
                f"sent={result['sent']} would_send={result['would_send']} "
                f"sent_today={result['sent_today']}"),
    ))
    db.commit()
    return TaggingPrefEmailResponse(**result)


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
        "BLOCKED", "PARSER_ERROR",
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
