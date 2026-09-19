"""Application tracking + preferences routes (blueprint Steps 8, 16, 17)."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.application import Application
from app.models.company import Company
from app.models.match import CandidateMatch
from app.models.user import User
from app.models.vacancy import Vacancy
from app.schemas.application import (
    SettingsSchema, ApplicationResponse, ApplicationDetailResponse,
    StatusUpdateRequest, AnswerUpdateRequest, AnswerResponse,
)
from app.services.application_service import (
    get_or_create_settings, prepare_application, approve_application, mark_submitted,
    update_status, answer_question,
)

router = APIRouter(tags=["applications"])


def _enrichment(db: Session, apps: list[Application]) -> dict[str, dict]:
    """Batch-fetch vacancy/company/match display data for a set of
    applications -- id -> {vacancy_title, company_name, vacancy_location,
    match_score, match_band}. Avoids an N+1 query per row on the list page."""
    if not apps:
        return {}
    vacancies = {v.id: v for v in
                db.query(Vacancy).filter(Vacancy.id.in_({a.vacancy_id for a in apps})).all()}
    companies = {
        c.id: c.company_name
        for c in db.query(Company).filter(Company.id.in_({v.company_id for v in vacancies.values()})).all()
    }
    match_ids = {a.match_id for a in apps if a.match_id}
    matches = ({m.id: m for m in db.query(CandidateMatch).filter(CandidateMatch.id.in_(match_ids)).all()}
               if match_ids else {})

    out: dict[str, dict] = {}
    for a in apps:
        vac = vacancies.get(a.vacancy_id)
        m = matches.get(a.match_id) if a.match_id else None
        out[a.id] = {
            "vacancy_title": vac.title if vac else None,
            "company_name": companies.get(vac.company_id) if vac else None,
            "vacancy_location": vac.location if vac else None,
            "match_score": m.score if m else None,
            "match_band": m.band if m else None,
        }
    return out


def _enriched(db: Session, app: Application, cls=ApplicationResponse):
    extra = _enrichment(db, [app])[app.id]
    return cls.model_validate(app).model_copy(update=extra)


@router.get("/preferences", response_model=SettingsSchema)
def get_preferences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return SettingsSchema.model_validate(get_or_create_settings(db, user.id))


@router.put("/preferences", response_model=SettingsSchema)
def update_preferences(body: SettingsSchema, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    s = get_or_create_settings(db, user.id)
    for field, value in body.model_dump().items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return SettingsSchema.model_validate(s)


@router.post("/matches/{match_id}/prepare-application", response_model=ApplicationDetailResponse,
             status_code=status.HTTP_201_CREATED)
def prepare(match_id: str, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    return _enriched(db, prepare_application(db, user, match_id), ApplicationDetailResponse)


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(Application)
            .filter(Application.user_id == user.id, Application.deleted_at.is_(None))
            .order_by(Application.created_at.desc()).all())
    extra = _enrichment(db, rows)
    return [ApplicationResponse.model_validate(a).model_copy(update=extra[a.id]) for a in rows]


@router.get("/applications/{app_id}", response_model=ApplicationDetailResponse)
def get_application(app_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = db.get(Application, app_id)
    if app is None or app.user_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return _enriched(db, app, ApplicationDetailResponse)


@router.post("/applications/{app_id}/approve", response_model=ApplicationDetailResponse)
def approve(app_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _enriched(db, approve_application(db, user, app_id), ApplicationDetailResponse)


@router.post("/applications/{app_id}/auto-submit", response_model=ApplicationDetailResponse)
def auto_submit(app_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Attempt automated submission (Phase 2). Safety-bound: never bypasses CAPTCHA/
    login/MFA, respects per-source policy, and falls back to action-required."""
    from fastapi import HTTPException
    from app.models.application import Application
    from app.automation.engine import attempt_auto_submit
    app = db.get(Application, app_id)
    if app is None or app.user_id != user.id or app.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return _enriched(db, attempt_auto_submit(db, user, app), ApplicationDetailResponse)


@router.post("/applications/{app_id}/mark-submitted", response_model=ApplicationDetailResponse)
def submit(app_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _enriched(db, mark_submitted(db, user, app_id), ApplicationDetailResponse)


@router.post("/applications/{app_id}/status", response_model=ApplicationDetailResponse)
def set_status(app_id: str, body: StatusUpdateRequest, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    return _enriched(db, update_status(db, user, app_id, body.status.upper()), ApplicationDetailResponse)


@router.put("/applications/{app_id}/answers/{answer_id}", response_model=AnswerResponse)
def fill_answer(app_id: str, answer_id: str, body: AnswerUpdateRequest,
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return AnswerResponse.model_validate(answer_question(db, user, app_id, answer_id, body.value))
