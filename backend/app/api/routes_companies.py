"""Company database + URL-tester routes (blueprint Steps 4 & the URL tester).

Listing is available to any authenticated user; import, edit, and URL testing are
administrator-only (role-based access control).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    CompanyResponse, CompanyImportResult, UrlTestResult, AutomationPolicyRequest,
)
from app.services.csv_import import import_companies_from_csv
from app.services.url_tester import test_url, status_from_result

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
