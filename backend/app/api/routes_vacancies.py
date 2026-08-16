"""Vacancy discovery routes (blueprint Steps 5 & 21).

Scanning and source inspection are administrator-only. Vacancy listing/detail are
available to any authenticated user (candidates browse matched vacancies; the
matching module will layer per-candidate scoring on top in the next step).
"""
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource
from app.schemas.vacancy import (
    VacancyResponse, VacancyDetailResponse, VacancySourceResponse, ScanReportResponse,
)
from app.services.scan_service import scan_company

router = APIRouter(tags=["vacancies"])


@router.post("/companies/{company_id}/scan", response_model=list[ScanReportResponse],
             dependencies=[Depends(require_admin)])
def trigger_scan(company_id: str, check_robots: bool = True, db: Session = Depends(get_db)):
    """Manually scan a company's careers source now.

    In production this enqueues a background job; here it runs inline so an admin
    can trigger and inspect a scan on demand.
    """
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    reports = scan_company(db, company)
    return [ScanReportResponse(**asdict(r)) for r in reports]


@router.get("/companies/{company_id}/sources", response_model=list[VacancySourceResponse],
            dependencies=[Depends(require_admin)])
def list_sources(company_id: str, db: Session = Depends(get_db)):
    rows = db.query(VacancySource).filter(VacancySource.company_id == company_id).all()
    return [VacancySourceResponse.model_validate(r) for r in rows]


@router.get("/companies/{company_id}/vacancies", response_model=list[VacancyResponse])
def list_company_vacancies(company_id: str, db: Session = Depends(get_db),
                           _: User = Depends(get_current_user),
                           is_open: bool | None = Query(default=True)):
    q = db.query(Vacancy).filter(Vacancy.company_id == company_id)
    if is_open is not None:
        q = q.filter(Vacancy.is_open == is_open)
    return [VacancyResponse.model_validate(v) for v in q.order_by(Vacancy.last_seen_at.desc()).all()]


@router.get("/vacancies", response_model=list[VacancyResponse])
def list_vacancies(db: Session = Depends(get_db), _: User = Depends(get_current_user),
                   q: str | None = Query(default=None, description="Search in title"),
                   is_open: bool | None = Query(default=True),
                   limit: int = Query(default=50, le=500), offset: int = Query(default=0, ge=0)):
    query = db.query(Vacancy)
    if is_open is not None:
        query = query.filter(Vacancy.is_open == is_open)
    if q:
        query = query.filter(Vacancy.title.ilike(f"%{q}%"))
    query = query.order_by(Vacancy.last_seen_at.desc()).offset(offset).limit(limit)
    return [VacancyResponse.model_validate(v) for v in query.all()]


@router.get("/vacancies/{vacancy_id}", response_model=VacancyDetailResponse)
def get_vacancy(vacancy_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    vac = db.get(Vacancy, vacancy_id)
    if vac is None or vac.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found.")
    return VacancyDetailResponse.model_validate(vac)
