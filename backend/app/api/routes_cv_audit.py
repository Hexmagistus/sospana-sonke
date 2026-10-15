"""ATS CV Audit & Rebuild ("CV Doctor") routes.

POST   /cv-audits                 run the full audit + rebuild on one uploaded CV
GET    /cv-audits                 list the candidate's audits
GET    /cv-audits/{id}            full result (findings, scores, rebuilt CV, checklist…)
PUT    /cv-audits/{id}/cv         save the candidate's edits; re-runs stress test & scores
POST   /cv-audits/{id}/apply-to-profile  copy the rebuilt CV into the profile (add-only, unconfirmed)
GET    /cv-audits/{id}/file/{kind}  download: docx | pdf | report
DELETE /cv-audits/{id}
"""
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.user import User
from app.schemas.cv_audit import (
    ApplyToProfileOptions, ApplyToProfileResult, CVAuditResponse, CVAuditSummary, RebuiltCV, RunAuditRequest,
)
from app.services import cv_audit_service as svc

router = APIRouter(prefix="/cv-audits", tags=["cv-audit"])


@router.post("", response_model=CVAuditResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour", key_func=user_or_ip_key)
def run_audit(request: Request, body: RunAuditRequest, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    return CVAuditResponse.model_validate(svc.run_audit(db, user, body.cv_id))


@router.get("", response_model=list[CVAuditSummary])
def list_audits(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [CVAuditSummary.model_validate(a) for a in svc.list_audits(db, user)]


@router.get("/{audit_id}", response_model=CVAuditResponse)
def get_audit(audit_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return CVAuditResponse.model_validate(svc.get_owned_audit(db, user, audit_id))


@router.put("/{audit_id}/cv", response_model=CVAuditResponse)
@limiter.limit("60/hour", key_func=user_or_ip_key)
def update_cv(request: Request, audit_id: str, body: RebuiltCV, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    return CVAuditResponse.model_validate(svc.update_rebuilt(db, user, audit_id, body.model_dump()))


@router.post("/{audit_id}/apply-to-profile", response_model=ApplyToProfileResult)
@limiter.limit("30/hour", key_func=user_or_ip_key)
def apply_to_profile(request: Request, audit_id: str, body: ApplyToProfileOptions | None = None,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    opts = (body or ApplyToProfileOptions()).model_dump()
    return ApplyToProfileResult(**svc.apply_audit_to_profile(db, user, audit_id, opts))


@router.get("/{audit_id}/file/{kind}")
@limiter.limit("120/hour", key_func=user_or_ip_key)
def download(request: Request, audit_id: str, kind: str, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    audit = svc.get_owned_audit(db, user, audit_id)
    data, media, filename = svc.file_bytes(audit, kind)
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"',
                             "Cache-Control": "no-store"})


@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audit(audit_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc.delete_audit(db, user, audit_id)
