"""Notification routes (candidate) and scheduler routes (admin) — blueprint Steps 11, 22, 31."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.notification import Notification, JobRun, PushToken
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse, UnreadCountResponse, ScheduleResponse, ScheduleUpdateRequest, JobRunResponse,
    PushTokenRequest, PushTokenResponse,
)
from app.scheduler.registry import get_schedule, set_schedule, JOBS
from app.scheduler.runner import run_job, UnknownJob

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


# ---- admin scheduler ----

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
