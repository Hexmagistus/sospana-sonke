"""Dashboard and report routes (blueprint Steps 10, sections 18, 19, 21, 44)."""
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.notifications.links import validated_notice_url

from app.core.deps import get_current_user, require_admin
from app.core.http_cache import private_short_cache
from app.db.session import get_db
from app.models.admin_ops import AdminAuditLog, UserTag
from app.models.report import Report
from app.models.user import User
from app.schemas.report import AdminDashboardResponse, CandidateDashboardResponse, ReportResponse
from app.services.dashboard_service import admin_dashboard, admin_analytics, candidate_dashboard
from app.services.report_service import generate_candidate_report
from app.services.storage import get_storage

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=CandidateDashboardResponse)
def get_candidate_dashboard(response: Response, db: Session = Depends(get_db),
                            user: User = Depends(get_current_user)):
    """Candidate-facing home base: at-a-glance counts across matches, CVs,
    cover letters and applications, plus subscription status. The service
    function and response schema behind this were already fully built -- this
    route was the only missing piece (see tests/test_dashboard.py)."""
    private_short_cache(response, max_age=15, swr=45)
    return CandidateDashboardResponse(**candidate_dashboard(db, user))


@router.get("/admin/dashboard", response_model=AdminDashboardResponse,
            dependencies=[Depends(require_admin)])
def get_admin_dashboard(db: Session = Depends(get_db)):
    return AdminDashboardResponse(**admin_dashboard(db))


@router.get("/admin/analytics", dependencies=[Depends(require_admin)])
def get_admin_analytics(db: Session = Depends(get_db)):
    return admin_analytics(db)


_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{0,39}$")


class TagRequest(BaseModel):
    tag: str = Field(min_length=1, max_length=40)
    # When the admin pasted a vacancy, careers, or apply URL, the tagged
    # person gets that link in their notice. Empty means tag only.
    link_url: str | None = Field(default=None, max_length=2000)

    @field_validator("link_url")
    @classmethod
    def _link(cls, value: str | None) -> str | None:
        return validated_notice_url(value)


def _eligible_for_alerts(user: User) -> bool:
    return bool(
        user.role == "candidate"
        and user.is_active
        and user.notify_opportunity_alerts
        and (user.preferred_position or "").strip()
    )


def _audit(db: Session, admin_id: str, action: str, target_user_id: str | None, detail: str) -> None:
    db.add(AdminAuditLog(
        admin_id=admin_id,
        action=action[:40],
        target_user_id=target_user_id,
        detail=detail[:500],
    ))


@router.get("/admin/users", dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db), limit: int = 1000,
               with_preference: bool = Query(default=False)):
    """Every registered account, newest first — email, contact, and whether they
    have built a candidate profile. Admin-only.

    with_preference=true keeps only people who typed a preferred post.
    """
    from app.models.profile import CandidateProfile
    profiles = {p.user_id: p for p in db.query(CandidateProfile).all()}
    q = db.query(User).order_by(User.created_at.desc())
    if with_preference:
        q = q.filter(User.preferred_position.isnot(None), User.preferred_position != "")
    rows = q.limit(min(limit, 1000)).all()
    tags_by_user: dict[str, list[str]] = {}
    if rows:
        ids = [u.id for u in rows]
        for tag in db.query(UserTag).filter(UserTag.user_id.in_(ids)).all():
            tags_by_user.setdefault(tag.user_id, []).append(tag.tag)
    out = []
    for u in rows:
        p = profiles.get(u.id)
        out.append({
            "id": u.id,
            "email": u.email,
            "name": f"{u.first_name} {u.last_name}".strip(),
            "mobile_number": u.mobile_number,
            "preferred_position": u.preferred_position,
            "qualification_name": u.qualification_name,
            "role": u.role,
            "email_verified": u.email_verified,
            "is_active": u.is_active,
            "notify_opportunity_alerts": bool(u.notify_opportunity_alerts),
            "tags": tags_by_user.get(u.id, []),
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "has_profile": p is not None,
            "city": p.city if p else None,
            "current_occupation": p.current_occupation if p else None,
        })
    return out


@router.post("/admin/users/{user_id}/tags", dependencies=[Depends(require_admin)])
def add_user_tag(user_id: str, body: TagRequest, db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    """Tag someone who opted in and named a preferred post. Writes an audit row."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not _eligible_for_alerts(target):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This person has not opted in to opportunity alerts, or has not set a preferred post.",
        )
    tag = " ".join(body.tag.split())
    if not _TAG.match(tag):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Tags use letters, numbers, spaces and hyphens, up to 40 characters.")
    existing = db.query(UserTag).filter(UserTag.user_id == target.id, UserTag.tag == tag).first()
    if existing is None:
        db.add(UserTag(user_id=target.id, tag=tag, created_by=admin.id))
    notice_sent = 0
    notice_duplicate = 0
    if body.link_url:
        from app.services.notification_service import notify_admin_suggestion
        notice_sent, notice_duplicate = notify_admin_suggestion(
            db, users=[target], title=tag,
            body="The Sospana Sonke team tagged you for this opening.",
            link_url=body.link_url,
        )
    _audit(db, admin.id, "tag", target.id,
           f"tag={tag} link={1 if body.link_url else 0} sent={notice_sent}")
    db.commit()
    tags = [t.tag for t in db.query(UserTag).filter(UserTag.user_id == target.id).all()]
    return {
        "user_id": target.id,
        "tags": tags,
        "notice_sent": notice_sent,
        "notice_duplicate": notice_duplicate,
    }


@router.delete("/admin/users/{user_id}/tags/{tag}", dependencies=[Depends(require_admin)])
def remove_user_tag(user_id: str, tag: str, db: Session = Depends(get_db),
                    admin: User = Depends(require_admin)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    row = db.query(UserTag).filter(UserTag.user_id == user_id, UserTag.tag == tag).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    db.delete(row)
    _audit(db, admin.id, "untag", target.id, f"tag={tag}")
    db.commit()
    return {"user_id": target.id, "removed": tag}


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
