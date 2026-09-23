"""Vacancy discovery routes (blueprint Steps 5 & 21).

Scanning and source inspection are administrator-only. Vacancy listing/detail are
available to any authenticated user (candidates browse matched vacancies; the
matching module will layer per-candidate scoring on top in the next step).
"""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone, date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource
from app.models.vacancy_report import VacancyReport, VACANCY_REPORT_CATEGORIES
from app.schemas.vacancy import (
    VacancyResponse, VacancyDetailResponse, VacancySourceResponse, ScanReportResponse,
    VacancyReportCreate, VacancyReportResponse, DuplicateGroupResponse,
    MergeDuplicatesRequest, MergeDuplicatesResponse,
)
from app.services.scan_service import scan_company
from app.services.duplicate_service import find_duplicate_groups, merge_duplicates
from app.services.vacancy_report_service import create_vacancy_report

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
    if is_open:
        # Even a role a scan hasn't re-checked yet drops off once its own
        # advertised closing date has passed -- see list_vacancies below.
        today = date.today()
        q = q.filter((Vacancy.closing_date.is_(None)) | (Vacancy.closing_date >= today))
    return [VacancyResponse.model_validate(v) for v in q.order_by(Vacancy.last_seen_at.desc()).all()]


@router.get("/vacancies", response_model=list[VacancyResponse])
@limiter.limit("600/hour", key_func=user_or_ip_key)
def list_vacancies(request: Request, db: Session = Depends(get_db), _: User = Depends(get_current_user),
                   q: str | None = Query(default=None, description="Search in title"),
                   is_open: bool | None = Query(default=True),
                   province: str | None = Query(
                       default=None, description="South African province, e.g. 'Gauteng' (best-effort field)."),
                   employment_type: str | None = Query(default=None, description="Substring match, e.g. 'Internship'."),
                   min_salary: int | None = Query(
                       default=None, ge=0, description="Monthly ZAR. Matches listings whose parsed salary_max is at least this."),
                   max_salary: int | None = Query(
                       default=None, ge=0, description="Monthly ZAR. Matches listings whose parsed salary_min is at most this."),
                   nqf_level: int | None = Query(
                       default=None, ge=1, le=10, description="Estimated NQF level (1-10) required by the listing."),
                   flagged: bool | None = Query(
                       default=None, description="True: only listings with a trust/safety flag. False: only listings with none."),
                   max_age_days: int | None = Query(
                       default=None, ge=1,
                       description="Only vacancies last seen within this many days (drops stale/old listings)."),
                   limit: int = Query(default=50, le=200), offset: int = Query(default=0, ge=0)):
    query = db.query(Vacancy)
    if is_open is not None:
        query = query.filter(Vacancy.is_open == is_open)
    if is_open:
        # Exclude outdated ads by default: a listing whose own advertised
        # closing date has passed drops out of results even if a re-scan
        # hasn't yet confirmed the role is gone (is_open only flips to False
        # once a fresh scan of the source no longer sees it -- see
        # scan_service.scan_source). Applied unconditionally, not just under
        # max_age_days, so callers get outdated-ad exclusion without having
        # to opt in.
        today = date.today()
        query = query.filter((Vacancy.closing_date.is_(None)) | (Vacancy.closing_date >= today))
    if q:
        query = query.filter(Vacancy.title.ilike(f"%{q}%"))
    if province:
        query = query.filter(Vacancy.province == province)
    if employment_type:
        query = query.filter(Vacancy.employment_type.ilike(f"%{employment_type}%"))
    if min_salary is not None:
        query = query.filter(Vacancy.salary_max.is_not(None), Vacancy.salary_max >= min_salary)
    if max_salary is not None:
        query = query.filter(Vacancy.salary_min.is_not(None), Vacancy.salary_min <= max_salary)
    if nqf_level is not None:
        query = query.filter(Vacancy.nqf_level == nqf_level)
    if max_age_days is not None:
        # Drop listings we haven't seen on the employer's careers page
        # recently. (The closing-date exclusion above already handles
        # outdated ads; this additionally drops listings that are merely
        # stale from the scanner's point of view.)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        query = query.filter(Vacancy.last_seen_at >= cutoff)
    if flagged is not None:
        # trust_flags is a JSON column -- filtering on "is the array non-empty"
        # portably across SQLite (tests) and Postgres (production) is awkward in
        # pure SQL, so this filters in Python over a bounded, already-ordered
        # window rather than adding a dialect-specific JSON expression.
        query = query.order_by(Vacancy.last_seen_at.desc()).limit(2000)
        candidates = [v for v in query.all() if bool(v.trust_flags) == flagged]
        return [VacancyResponse.model_validate(v) for v in candidates[offset:offset + limit]]
    query = query.order_by(Vacancy.last_seen_at.desc()).offset(offset).limit(limit)
    return [VacancyResponse.model_validate(v) for v in query.all()]


@router.get("/vacancies/{vacancy_id}", response_model=VacancyDetailResponse)
def get_vacancy(vacancy_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    vac = db.get(Vacancy, vacancy_id)
    if vac is None or vac.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found.")
    return VacancyDetailResponse.model_validate(vac)


@router.post("/vacancies/{vacancy_id}/report", response_model=VacancyReportResponse,
             status_code=status.HTTP_201_CREATED)
def report_vacancy(vacancy_id: str, body: VacancyReportCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Candidate-facing "Report this opportunity" (scam / expired / incorrect /
    duplicate / misleading / other) -- queued for admin triage, never auto-acted on."""
    report = create_vacancy_report(db, user_id=user.id, vacancy_id=vacancy_id,
                                   category=body.category, details=body.details)
    return VacancyReportResponse.model_validate(report)


@router.get("/admin/vacancy-reports", response_model=list[VacancyReportResponse],
            dependencies=[Depends(require_admin)])
def list_vacancy_reports(db: Session = Depends(get_db),
                         status_filter: str | None = Query(default=None, alias="status")):
    q = db.query(VacancyReport)
    if status_filter:
        q = q.filter(VacancyReport.status == status_filter)
    return [VacancyReportResponse.model_validate(r)
            for r in q.order_by(VacancyReport.created_at.desc()).all()]


@router.get("/admin/vacancies/duplicates", response_model=list[DuplicateGroupResponse],
            dependencies=[Depends(require_admin)])
def list_duplicate_vacancies(db: Session = Depends(get_db),
                             company_id: str | None = Query(default=None)):
    groups = find_duplicate_groups(db, company_id=company_id)
    return [
        DuplicateGroupResponse(
            keep=VacancyResponse.model_validate(g.keep),
            duplicates=[VacancyResponse.model_validate(d) for d in g.duplicates],
        )
        for g in groups
    ]


@router.post("/admin/vacancies/merge", response_model=MergeDuplicatesResponse,
             dependencies=[Depends(require_admin)])
def merge_duplicate_vacancies(body: MergeDuplicatesRequest, db: Session = Depends(get_db)):
    merged = merge_duplicates(db, keep_id=body.keep_id, duplicate_ids=body.duplicate_ids)
    return MergeDuplicatesResponse(merged=merged)
