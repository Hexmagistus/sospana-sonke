"""Candidate matching routes (blueprint Steps 6 & 10) + admin match config.

Candidates run and view their own matches; the scoring is deterministic and every
match is explainable (reasons + gaps). Weights/thresholds are admin-configurable.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.company import Company
from app.models.match import CandidateMatch
from app.models.user import User
from app.models.vacancy import Vacancy
from app.matching.config import MatchConfig
from app.schemas.match import (
    MatchResponse, MatchDetailResponse, MatchRunResponse, MatchConfigSchema,
)
from app.services.match_service import run_match_for_user, get_match_config, set_match_config
from app.services.subscription_service import require_active_subscription

router = APIRouter(tags=["matches"])


def _to_response(db: Session, m: CandidateMatch, detail: bool = False):
    vac = db.get(Vacancy, m.vacancy_id)
    company = db.get(Company, vac.company_id) if vac else None
    base = dict(
        id=m.id, vacancy_id=m.vacancy_id,
        vacancy_title=vac.title if vac else None,
        company_name=company.company_name if company else None,
        score=m.score, band=m.band, decision=m.decision, confidence=m.confidence,
        hard_ok=m.hard_ok, status=m.status, created_at=m.created_at,
    )
    if not detail:
        return MatchResponse(**base)
    return MatchDetailResponse(**base, sub_scores=m.sub_scores, reasons=m.reasons,
                               gaps=m.gaps, engine_version=m.engine_version)


@router.post("/matches/run", response_model=MatchRunResponse)
def run_matches(db: Session = Depends(get_db), user: User = Depends(require_active_subscription)):
    """Run the matching engine for the current candidate over all open vacancies."""
    from app.services.application_service import get_or_create_settings
    s = get_or_create_settings(db, user.id)
    summary = run_match_for_user(
        db, user.id,
        excluded_companies={c.strip().lower() for c in (s.excluded_companies or [])},
        excluded_roles={r.strip().lower() for r in (s.excluded_roles or [])},
    )
    return MatchRunResponse(
        considered=summary.considered, prefiltered_out=summary.prefiltered_out,
        matched=summary.matched, rejected=summary.rejected,
        created=summary.created, updated=summary.updated,
    )


@router.get("/matches", response_model=list[MatchResponse])
def list_matches(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                 decision: str | None = Query(default=None),
                 min_score: float | None = Query(default=None),
                 limit: int = Query(default=100, le=500), offset: int = Query(default=0, ge=0)):
    q = db.query(CandidateMatch).filter(CandidateMatch.user_id == user.id)
    if decision:
        q = q.filter(CandidateMatch.decision == decision.upper())
    if min_score is not None:
        q = q.filter(CandidateMatch.score >= min_score)
    matches = q.order_by(CandidateMatch.score.desc()).offset(offset).limit(limit).all()

    # Batch-load vacancies and companies to avoid an N+1 query per match.
    vac_ids = {m.vacancy_id for m in matches}
    vacs = {v.id: v for v in db.query(Vacancy).filter(Vacancy.id.in_(vac_ids)).all()} if vac_ids else {}
    company_ids = {v.company_id for v in vacs.values()}
    companies = ({c.id: c for c in db.query(Company).filter(Company.id.in_(company_ids)).all()}
                 if company_ids else {})

    out = []
    for m in matches:
        vac = vacs.get(m.vacancy_id)
        company = companies.get(vac.company_id) if vac else None
        out.append(MatchResponse(
            id=m.id, vacancy_id=m.vacancy_id,
            vacancy_title=vac.title if vac else None,
            company_name=company.company_name if company else None,
            score=m.score, band=m.band, decision=m.decision, confidence=m.confidence,
            hard_ok=m.hard_ok, status=m.status, created_at=m.created_at,
        ))
    return out


@router.get("/matches/{match_id}", response_model=MatchDetailResponse)
def get_match(match_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.get(CandidateMatch, match_id)
    if m is None or m.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    return _to_response(db, m, detail=True)


@router.post("/matches/{match_id}/interview-prep", status_code=status.HTTP_201_CREATED)
def create_interview_prep(match_id: str, db: Session = Depends(get_db),
                          user: User = Depends(require_active_subscription)):
    from app.schemas.interview import InterviewPrepResponse
    from app.services.interview_service import generate_interview_prep
    return InterviewPrepResponse.model_validate(generate_interview_prep(db, user, match_id))


@router.get("/matches/{match_id}/interview-prep")
def get_interview_prep(match_id: str, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    from fastapi import HTTPException
    from app.models.interview import InterviewPrep
    from app.schemas.interview import InterviewPrepResponse
    prep = (db.query(InterviewPrep)
            .filter(InterviewPrep.user_id == user.id, InterviewPrep.match_id == match_id)
            .order_by(InterviewPrep.created_at.desc()).first())
    if prep is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No interview prep yet.")
    return InterviewPrepResponse.model_validate(prep)


@router.get("/admin/match-config", response_model=MatchConfigSchema, dependencies=[Depends(require_admin)])
def read_match_config(db: Session = Depends(get_db)):
    return MatchConfigSchema(**get_match_config(db).to_dict())


@router.put("/admin/match-config", response_model=MatchConfigSchema, dependencies=[Depends(require_admin)])
def update_match_config(body: MatchConfigSchema, db: Session = Depends(get_db)):
    cfg = MatchConfig.from_dict(body.model_dump())
    set_match_config(db, cfg)
    return MatchConfigSchema(**cfg.to_dict())
