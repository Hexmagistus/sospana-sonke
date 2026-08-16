"""Application lifecycle orchestration (blueprint sections 13-17, 30).

Prepares applications from matches (with anti-spam caps, duplicate prevention, and
a minimum-score gate), records a full audit trail of every transition, and never
fabricates factual answers. Because browser automation is a Phase 2 capability, an
approved/automatic application in Phase 1 resolves to CANDIDATE_ACTION_REQUIRED
with a ready-to-submit package and clear instructions — it is never silently
"submitted" on the candidate's behalf without them acting.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status as http
from sqlalchemy.orm import Session

from app.applications.answers import generate_standard_answers
from app.models.application import (
    Application, ApplicationAnswer, ApplicationEvent, ApplicationSettings, CANDIDATE_SETTABLE,
)
from app.models.company import Company
from app.models.document import CVVersion, CoverLetter
from app.models.match import CandidateMatch
from app.models.user import User
from app.models.vacancy import Vacancy
from app.services.document_service import _facts_and_truth
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


def _count_since(db: Session, user_id: str, since: datetime) -> int:
    return (db.query(Application)
            .filter(Application.user_id == user_id, Application.created_at >= since)
            .count())


def _latest_document_ids(db: Session, user_id: str, match_id: str):
    cv = (db.query(CVVersion)
          .filter(CVVersion.user_id == user_id, CVVersion.match_id == match_id)
          .order_by(CVVersion.created_at.desc()).first())
    cl = (db.query(CoverLetter)
          .filter(CoverLetter.user_id == user_id, CoverLetter.match_id == match_id)
          .order_by(CoverLetter.created_at.desc()).first())
    return (cv.id if cv else None), (cl.id if cl else None)


# ---- prepare ----------------------------------------------------------------

def prepare_application(db: Session, user: User, match_id: str) -> Application:
    match = db.get(CandidateMatch, match_id)
    if match is None or match.user_id != user.id:
        raise HTTPException(status_code=http.HTTP_404_NOT_FOUND, detail="Match not found.")

    settings = get_or_create_settings(db, user.id)

    if match.decision == "DO_NOT_APPLY":
        raise HTTPException(status_code=http.HTTP_409_CONFLICT,
                            detail="The match decision is DO NOT APPLY; preparation is blocked.")
    if match.score < settings.min_match_score:
        raise HTTPException(status_code=http.HTTP_409_CONFLICT,
                            detail=f"Match score {match.score} is below your minimum ({settings.min_match_score}).")

    if db.query(Application).filter(Application.user_id == user.id,
                                    Application.vacancy_id == match.vacancy_id).first():
        raise HTTPException(status_code=http.HTTP_409_CONFLICT,
                            detail="You already have an application for this vacancy.")

    now = datetime.now(timezone.utc)
    if _count_since(db, user.id, now - timedelta(days=1)) >= settings.max_applications_per_day:
        raise HTTPException(status_code=http.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Daily application limit ({settings.max_applications_per_day}) reached.")
    if _count_since(db, user.id, now - timedelta(days=7)) >= settings.max_applications_per_week:
        raise HTTPException(status_code=http.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Weekly application limit ({settings.max_applications_per_week}) reached.")

    vac = db.get(Vacancy, match.vacancy_id)
    company = db.get(Company, vac.company_id) if vac else None
    cv_id, cl_id = _latest_document_ids(db, user.id, match.id)

    mode = settings.application_mode
    # Phase 1 has no browser automation: automatic/assisted both need the candidate
    # to submit; approval waits for the candidate to authorise first.
    if mode == "approval":
        new_status = "AWAITING_APPROVAL"
        note = "Review the prepared application and approve it to authorise submission."
    else:  # automatic or assisted
        new_status = "CANDIDATE_ACTION_REQUIRED"
        note = ("Open the application link, attach your generated CV and cover letter, answer any "
                "questions marked UNKNOWN, and submit. (Automated submission arrives in a later phase.)")

    app = Application(user_id=user.id, vacancy_id=vac.id, match_id=match.id,
                      cv_version_id=cv_id, cover_letter_id=cl_id, mode=mode, status=new_status,
                      application_url=vac.application_url, action_required_note=note)
    db.add(app)
    db.flush()

    facts, _ = _facts_and_truth(db, user)
    for a in generate_standard_answers(facts, company.company_name if company else None,
                                       vac.title if vac else None):
        db.add(ApplicationAnswer(application_id=app.id, **a))

    _log(db, app, "prepared", actor="system", status_to=new_status,
         detail=f"Prepared in '{mode}' mode.")
    match.status = new_status
    if new_status == "CANDIDATE_ACTION_REQUIRED":
        notify_action_required(db, user=user, application=app,
                               vacancy_title=vac.title if vac else "a role",
                               company_name=company.company_name if company else "an employer")
    db.commit()
    db.refresh(app)
    return app


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
