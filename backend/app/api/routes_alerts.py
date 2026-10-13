"""Saved daily-role alerts. Auth required. The preview sends no email."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.role_alert import AlertPreviewResponse, RoleAlertResponse, RoleAlertWrite
from app.services import role_alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[RoleAlertResponse])
@limiter.limit("60/minute")
def list_my_alerts(request: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    return [RoleAlertResponse.model_validate(row) for row in role_alerts.list_alerts(db, user.id)]


@router.post("", response_model=RoleAlertResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def create_my_alert(request: Request, body: RoleAlertWrite, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    row = role_alerts.create_alert(
        db, user, country=body.country, category=body.category, keyword=body.keyword,
        opportunity_type=body.opportunity_type,
    )
    return RoleAlertResponse.model_validate(row)


@router.get("/preview", response_model=AlertPreviewResponse)
@limiter.limit("10/hour")
def preview_my_alerts(request: Request, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Dry run for this account only. ``email_sent`` is always false."""
    return AlertPreviewResponse.model_validate(role_alerts.preview(db, user))


@router.put("/{alert_id}", response_model=RoleAlertResponse)
@limiter.limit("30/hour")
def update_my_alert(request: Request, alert_id: str, body: RoleAlertWrite,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = role_alerts.update_alert(
        db, user, alert_id, country=body.country, category=body.category, keyword=body.keyword,
        opportunity_type=body.opportunity_type,
    )
    return RoleAlertResponse.model_validate(row)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/hour")
def delete_my_alert(request: Request, alert_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    role_alerts.delete_alert(db, user.id, alert_id)
