"""Dashboard and report routes (blueprint Steps 10, sections 18, 19, 21, 44)."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.report import CandidateDashboardResponse, AdminDashboardResponse, ReportResponse
from app.services.dashboard_service import candidate_dashboard, admin_dashboard, admin_analytics
from app.services.report_service import generate_candidate_report
from app.services.storage import get_storage

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=CandidateDashboardResponse)
def get_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return CandidateDashboardResponse(**candidate_dashboard(db, user))


@router.get("/admin/dashboard", response_model=AdminDashboardResponse,
            dependencies=[Depends(require_admin)])
def get_admin_dashboard(db: Session = Depends(get_db)):
    return AdminDashboardResponse(**admin_dashboard(db))


@router.get("/admin/analytics", dependencies=[Depends(require_admin)])
def get_admin_analytics(db: Session = Depends(get_db)):
    return admin_analytics(db)


@router.post("/reports/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ReportResponse.model_validate(generate_candidate_report(db, user))


@router.get("/reports", response_model=list[ReportResponse])
def list_reports(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(Report).filter(Report.user_id == user.id, Report.deleted_at.is_(None))
            .order_by(Report.created_at.desc()).all())
    return [ReportResponse.model_validate(r) for r in rows]


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Report, report_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return ReportResponse.model_validate(r)


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Report, report_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    data = get_storage().get(r.storage_key_pdf)
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{r.label}.pdf"'})
