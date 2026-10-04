"""Application lifecycle orchestration (blueprint sections 13-17, 30).

Moves an existing application through its lifecycle, records a full audit trail of
every transition, and never fabricates factual answers. (Applications are no longer
prepared from job matches: matching was removed.) Because browser automation is a Phase 2 capability, an
approved/automatic application in Phase 1 resolves to CANDIDATE_ACTION_REQUIRED
with a ready-to-submit package and clear instructions — it is never silently
"submitted" on the candidate's behalf without them acting.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status as http
from sqlalchemy.orm import Session

from app.models.application import (
    Application, ApplicationAnswer, ApplicationEvent, ApplicationSettings, CANDIDATE_SETTABLE,
)
from app.models.company import Company
from app.models.user import User
from app.models.vacancy import Vacancy
from app.services.notification_service import notify_action_required


# ---- settings ---------------------------------------------------------------

def get_or_create_settings(db: Session, user_id: str) -> ApplicationSettings:
    s = db.query(ApplicationSettings).filter(ApplicationSettings.user_id == user_id).first()
    if s is None:
        s = ApplicationSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


# ---- helpers ----------------------------------------------------------------

def _log(db: Session, app: Application, event_type: str, actor: str = "system",
         status_from: str | None = None, status_to: str | None = None, detail: str | None = None):
    db.add(ApplicationEvent(application_id=app.id, event_type=event_type, actor=actor,
                            status_from=status_from, status_to=status_to, detail=detail))


def _transition(db: Session, app: Application, new_status: str, event_type: str,
                actor: str = "system", detail: str | None = None):
    old = app.status
    app.status = new_status
    _log(db, app, event_type, actor=actor, status_from=old, status_to=new_status, detail=detail)


# ---- transitions ------------------------------------------------------------

def _owned(db: Session, user: User, app_id: str) -> Application:
    app = db.get(Application, app_id)
    if app is None or app.user_id != user.id or app.deleted_at is not None:
        raise HTTPException(status_code=http.HTTP_404_NOT_FOUND, detail="Application not found.")
    return app


def approve_application(db: Session, user: User, app_id: str) -> Application:
    app = _owned(db, user, app_id)
    if app.status != "AWAITING_APPROVAL":
        raise HTTPException(status_code=http.HTTP_409_CONFLICT,
                            detail=f"Cannot approve an application in status {app.status}.")
    app.authorised_at = datetime.now(timezone.utc)
    _transition(db, app, "CANDIDATE_ACTION_REQUIRED", "approved", actor="candidate",
                detail="Candidate authorised submission. Ready-to-submit package prepared.")
    app.action_required_note = ("You approved this application. Open the link and submit; "
                                "mark it as submitted once done.")
    vac = db.get(Vacancy, app.vacancy_id)
    company = db.get(Company, vac.company_id) if vac else None
    notify_action_required(db, user=user, application=app,
                           vacancy_title=vac.title if vac else "a role",
                           company_name=company.company_name if company else "an employer")
    db.commit()
    db.refresh(app)
    return app


def mark_submitted(db: Session, user: User, app_id: str) -> Application:
    app = _owned(db, user, app_id)
    if app.status not in ("AWAITING_APPROVAL", "CANDIDATE_ACTION_REQUIRED", "APPLICATION_PREPARED"):
        raise HTTPException(status_code=http.HTTP_409_CONFLICT,
                            detail=f"Cannot mark submitted from status {app.status}.")
    app.submitted_at = datetime.now(timezone.utc)
    app.submission_method = "manual"
    _transition(db, app, "SUBMITTED", "submitted", actor="candidate",
                detail="Candidate confirmed the application was submitted.")
    db.commit()
    db.refresh(app)
    return app


def update_status(db: Session, user: User, app_id: str, new_status: str) -> Application:
    app = _owned(db, user, app_id)
    if new_status not in CANDIDATE_SETTABLE:
        raise HTTPException(status_code=http.HTTP_400_BAD_REQUEST,
                            detail=f"Status '{new_status}' is not one you can set directly.")
    _transition(db, app, new_status, "status_update", actor="candidate")
    db.commit()
    db.refresh(app)
    return app


def answer_question(db: Session, user: User, app_id: str, answer_id: str, value: str) -> ApplicationAnswer:
    app = _owned(db, user, app_id)
    ans = db.get(ApplicationAnswer, answer_id)
    if ans is None or ans.application_id != app.id:
        raise HTTPException(status_code=http.HTTP_404_NOT_FOUND, detail="Answer not found.")
    ans.answer = value
    ans.source = "candidate"
    ans.is_unknown = False
    _log(db, app, "answer_filled", actor="candidate", detail=f"Answered: {ans.question[:80]}")
    db.commit()
    db.refresh(ans)
    return ans
