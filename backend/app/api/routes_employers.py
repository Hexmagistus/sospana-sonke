"""Public pages for employers that have a careers link. No sign-in. No notes."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session, defer

from app.api.routes_vacancies import _public_job
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.company import Company
from app.models.vacancy import Vacancy
from app.schemas.employer import (
    PublicEmployerIdsResponse,
    PublicEmployerListResponse,
    PublicEmployerResponse,
    PublicEmployerSummary,
)
from app.services.opportunity_expiry import public_role_clauses
from app.services.scan_runner import country_band

router = APIRouter(prefix="/employers", tags=["employers"])

_ROLE_SAMPLE = 20
_LIST_DEFER = (
    defer(Vacancy.description),
    defer(Vacancy.raw_content),
    defer(Vacancy.requirements_text),
    defer(Vacancy.qualifications),
    defer(Vacancy.experience),
)


def _linked():
    return (
        Company.deleted_at.is_(None),
        Company.active.is_(True),
        Company.careers_url.isnot(None),
        func.length(func.trim(Company.careers_url)) > 0,
    )


def stored_careers_scope(notes: str | None) -> str | None:
    """The global-board marker, without returning the note that carries it."""
    if notes and "careers_scope=global" in notes:
        return "global"
    return None


@router.get("", response_model=PublicEmployerListResponse)
@limiter.limit("60/minute")
def list_public_employers(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=20000),
):
    """Employers with a careers link, in the standing country order."""
    response.headers["Cache-Control"] = "public, max-age=300"
    rows = (
        db.query(Company.id, Company.company_name, Company.country, Company.source_type)
        .filter(*_linked())
        .all()
    )
    rows.sort(key=lambda row: (
        country_band(row.country),
        (row.country or "").casefold(),
        (row.company_name or "").casefold(),
    ))
    page = rows[offset:offset + limit]
    return PublicEmployerListResponse(
        employers=[
            PublicEmployerSummary(
                id=row.id,
                company_name=row.company_name,
                country=row.country,
                source_type=row.source_type,
            )
            for row in page
        ],
        matched=len(rows),
        limit=limit,
        offset=offset,
    )


@router.get("/ids", response_model=PublicEmployerIdsResponse)
@limiter.limit("30/minute")
def list_public_employer_ids(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(default=5000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0, le=20000),
):
    """Ids for the sitemap, in the same order as the public list. One query."""
    response.headers["Cache-Control"] = "public, max-age=300"
    rows = db.query(Company.id, Company.country, Company.company_name).filter(*_linked()).all()
    rows.sort(key=lambda row: (
        country_band(row.country),
        (row.country or "").casefold(),
        (row.company_name or "").casefold(),
    ))
    page = rows[offset:offset + limit]
    return PublicEmployerIdsResponse(
        ids=[row.id for row in page],
        matched=len(rows),
        limit=limit,
        offset=offset,
    )


@router.get("/{company_id}", response_model=PublicEmployerResponse)
@limiter.limit("120/minute")
def public_employer(
    request: Request,
    company_id: str,
    response: Response,
    db: Session = Depends(get_db),
):
    """One employer with a careers link, plus the open roles we have stored."""
    response.headers["Cache-Control"] = "public, max-age=60"
    company = db.get(Company, company_id)
    url = (company.careers_url or "").strip() if company is not None else ""
    if (
        company is None
        or company.deleted_at is not None
        or not company.active
        or not url
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No public employer page.")
    roles = (
        db.query(Vacancy)
        .options(*_LIST_DEFER)
        .filter(Vacancy.company_id == company.id, *public_role_clauses())
        .order_by(Vacancy.last_seen_at.desc())
    )
    count = roles.count()
    sample = roles.limit(_ROLE_SAMPLE).all()
    return PublicEmployerResponse(
        id=company.id,
        company_name=company.company_name,
        country=company.country,
        source_type=company.source_type,
        careers_url=url,
        careers_scope=stored_careers_scope(company.notes),
        last_checked=company.last_checked,
        url_looks_like_careers=company.url_looks_like_careers,
        open_role_count=count,
        roles=[_public_job(role, company) for role in sample],
    )
