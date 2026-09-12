"""Company database + URL-tester routes (blueprint Steps 4 & the URL tester).

Listing is available to any authenticated user; import, edit, and URL testing are
administrator-only (role-based access control).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.company import Company
from app.models.link_report import LinkReport
from app.models.user import User
from app.schemas.company import (
    CompanyResponse, CompanyImportResult, UrlTestResult, AutomationPolicyRequest, CoverageRow,
    TrendingCompany,
)
from app.schemas.link_report import LinkReportCreateRequest, LinkReportResponse
from app.services.csv_import import import_companies_from_csv
from app.services.link_report_service import create_link_report
from app.services.logo_service import discover_favicon
from app.services.url_tester import test_url, status_from_result
from app.services.watch_service import trending_company_ids

_NEEDS_ATTENTION = {"needs_real_url", "needs_review", "no_url", "error"}

# How long a discovered (or "nothing found") icon result stays cached on the
# company row before we try that company's site again.
_FAVICON_RECHECK = timedelta(days=30)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    source_type: str | None = Query(default=None, description="Filter by JSE or SOE"),
    active: bool | None = Query(default=None),
    limit: int = Query(default=100, le=5000),
    offset: int = Query(default=0, ge=0),
):
    q = db.query(Company).filter(Company.deleted_at.is_(None))
    if source_type:
        q = q.filter(Company.source_type == source_type.upper())
    if active is not None:
        q = q.filter(Company.active == active)
    q = q.order_by(Company.company_name).offset(offset).limit(limit)
    return [CompanyResponse.model_validate(c) for c in q.all()]


@router.get("/coverage", response_model=list[CoverageRow])
def coverage_map(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Honest per-country/category rollup: how much of the directory is a
    verified working link vs. still pending verification vs. needs attention.
    Doubles as the team's own to-do list for filling gaps, not just a stat for
    users -- see the "Full-Africa university coverage" note in the project
    doc for why this matters for the rows added fastest (universities)."""
    buckets: dict[tuple[str, str], dict] = {}
    for c in db.query(Company).filter(Company.deleted_at.is_(None)).all():
        key = (c.country or "Unknown", (c.source_type or "").upper() or "OTHER")
        b = buckets.setdefault(key, {"total": 0, "active": 0, "with_careers_url": 0,
                                     "verified_ok": 0, "pending_verification": 0, "needs_attention": 0})
        b["total"] += 1
        b["active"] += int(c.active)
        b["with_careers_url"] += int(bool(c.careers_url))
        if c.scraping_status == "ok":
            b["verified_ok"] += 1
        elif c.scraping_status == "pending":
            b["pending_verification"] += 1
        elif c.scraping_status in _NEEDS_ATTENTION:
            b["needs_attention"] += 1
    rows = [CoverageRow(country=k[0], source_type=k[1], **v) for k, v in buckets.items()]
    rows.sort(key=lambda r: (r.country, r.source_type))
    return rows


@router.get("/trending", response_model=list[TrendingCompany])
def trending_companies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, le=200),
):
    """Companies picking up the most notify-me subscriptions lately -- powers
    the directory's 🔥 "Popular this week" badge. See trending_company_ids()
    for why this (and not shares, which aren't tracked) is the signal used."""
    rows = trending_company_ids(db, days=days, limit=limit)
    return [TrendingCompany(company_id=cid, watch_count=cnt) for cid, cnt in rows]


@router.post("/{company_id}/report-link", response_model=LinkReportResponse,
            status_code=status.HTTP_201_CREATED)
def report_broken_link(company_id: str, body: LinkReportCreateRequest,
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Crowd-sourced verification: let any signed-in candidate flag a link
    that's broken, wrong, or redirects elsewhere -- far faster at scale than
    waiting for the periodic re-check or an admin's manual URL test."""
    report = create_link_report(db, user_id=user.id, company_id=company_id, reason=body.reason)
    return LinkReportResponse.model_validate(report)


@router.get("/link-reports", response_model=list[LinkReportResponse], dependencies=[Depends(require_admin)])
def list_link_reports(db: Session = Depends(get_db),
                      status_filter: str | None = Query(default=None, alias="status"),
                      limit: int = Query(default=100, le=500)):
    q = db.query(LinkReport)
    if status_filter:
        q = q.filter(LinkReport.status == status_filter)
    q = q.order_by(LinkReport.created_at.desc()).limit(limit)
    return [LinkReportResponse.model_validate(r) for r in q.all()]


@router.get("/{company_id}/icon")
async def company_icon(company_id: str, db: Session = Depends(get_db)):
    """Redirect to the real icon pulled directly from this company's own page —
    not a guessed domain. Cached on the company row (see Company.favicon_url) so
    a given company's site is fetched at most once every 30 days.

    Intentionally unauthenticated: a plain <img src> can't send an Authorization
    header, and this only ever exposes a company's own already-public favicon —
    nothing about Sospana Sonke's data.
    """
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    # SQLite (used in tests/dev) drops tzinfo from DateTime(timezone=True) columns
    # on read-back, so normalise before comparing rather than assuming Postgres's
    # behaviour everywhere.
    checked_at = company.favicon_checked_at
    if checked_at is not None and checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    stale = checked_at is None or datetime.now(timezone.utc) - checked_at > _FAVICON_RECHECK
    if stale:
        company.favicon_url = await discover_favicon(company.official_website, company.careers_url)
        company.favicon_checked_at = datetime.now(timezone.utc)
        db.commit()

    if not company.favicon_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No icon found for this company.")
    return RedirectResponse(company.favicon_url, status_code=status.HTTP_302_FOUND)


@router.post("/import", response_model=CompanyImportResult, dependencies=[Depends(require_admin)])
async def import_companies(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a .csv file.")
    content = await file.read()
    return import_companies_from_csv(db, content)


@router.post("/{company_id}/test-url", response_model=UrlTestResult, dependencies=[Depends(require_admin)])
async def test_company_url(company_id: str, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    result = await test_url(company.careers_url)
    company.last_checked = datetime.now(timezone.utc)
    company.last_http_status = result.status_code
    company.last_final_url = result.final_url
    company.url_looks_like_careers = result.looks_like_careers
    company.scraping_status = status_from_result(result)
    db.commit()
    return result


@router.put("/{company_id}/automation-policy", response_model=CompanyResponse,
            dependencies=[Depends(require_admin)])
async def set_automation_policy(company_id: str, body: AutomationPolicyRequest,
                                db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    company.automation_mode = body.automation_mode
    company.requires_login = body.requires_login
    company.has_captcha = body.has_captcha
    db.commit()
    db.refresh(company)
    return CompanyResponse.model_validate(company)
