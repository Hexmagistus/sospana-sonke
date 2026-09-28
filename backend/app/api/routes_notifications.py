"""Notification routes (candidate) and scheduler routes (admin) — blueprint Steps 11, 22, 31."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.notification import Notification, JobRun, PushToken
from app.models.admin_ops import AdminAuditLog
from app.models.user import User
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.schemas.notification import (
    NotificationResponse, UnreadCountResponse, ScheduleResponse, ScheduleUpdateRequest, JobRunResponse,
    PushTokenRequest, PushTokenResponse, AdminSuggestionRequest, AdminSuggestionResponse,
    SourceHealthResponse, SourceHealthItem,
)
from app.scheduler.registry import get_schedule, set_schedule, JOBS
from app.scheduler.runner import run_job, UnknownJob
from app.services.notification_service import notify_admin_suggestion

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

def _can_receive_suggestion(user: User) -> bool:
    """POPIA: only an active candidate who named a preferred post and opted in."""
    return bool(
        user.role == "candidate"
        and user.is_active
        and not user.deleted_at
        and user.notify_opportunity_alerts
        and (user.preferred_position or "").strip()
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
    eligible = [u for u in targets if _can_receive_suggestion(u)]
    skipped = len(targets) - len(eligible)
    sent = notify_admin_suggestion(db, users=eligible, title=body.title, body=body.body,
                                   link_url=body.link_url) if eligible else 0
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action="notify",
        target_user_id=None,
        detail=f"sent={sent} skipped={skipped} title_len={len(body.title)}",
    ))
    db.commit()
    return AdminSuggestionResponse(sent=sent, skipped=skipped)


# ---- admin scheduler ----

@router.get("/admin/source-health", response_model=SourceHealthResponse, dependencies=[Depends(require_admin)])
def source_health(db: Session = Depends(get_db)):
    """Last success, last error, and counts per careers source. Numbers only
    plus the 20 most recently checked sources — not the whole directory."""
    sources = db.query(func.count(VacancySource.id)).scalar() or 0
    open_vacancies = (db.query(func.count(Vacancy.id)).filter(Vacancy.is_open.is_(True)).scalar() or 0)
    last_success_at = (db.query(func.max(VacancySource.last_checked))
                       .filter(VacancySource.last_status == "ok").scalar())
    by_status = {row[0] or "unknown": row[1] for row in
                 db.query(VacancySource.last_status, func.count(VacancySource.id))
                 .group_by(VacancySource.last_status).all()}
    by_ats = {row[0] or "unknown": row[1] for row in
              db.query(VacancySource.ats_type, func.count(VacancySource.id))
              .group_by(VacancySource.ats_type).all()}
    recent_rows = (db.query(VacancySource, Company.company_name, Company.country)
                   .join(Company, Company.id == VacancySource.company_id)
                   .order_by(VacancySource.last_checked.is_(None), VacancySource.last_checked.desc())
                   .limit(20).all())
    recent = [SourceHealthItem(
        company_name=name, country=country, ats_type=src.ats_type, url=src.url,
        last_status=src.last_status, last_error=src.last_error, last_checked=src.last_checked,
        last_vacancy_count=src.last_vacancy_count, consecutive_failures=src.consecutive_failures or 0,
    ) for src, name, country in recent_rows]
    return SourceHealthResponse(
        sources=sources, open_vacancies=open_vacancies, last_success_at=last_success_at,
        by_status=by_status, by_ats=by_ats, recent=recent,
    )

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
