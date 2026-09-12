"""Notify-me subscription routes (company/country/category alerts -- an
extension of blueprint section 31's alerting). See
app/services/watch_service.py and app/services/link_check_service.py for the
matching and alerting logic.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.watch import CompanyWatch
from app.schemas.watch import WatchCreateRequest, WatchResponse
from app.services.watch_service import create_watch, delete_watch

router = APIRouter(prefix="/watches", tags=["watches"])


@router.get("", response_model=list[WatchResponse])
def list_watches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(CompanyWatch)
            .filter(CompanyWatch.user_id == user.id, CompanyWatch.active.is_(True))
            .order_by(CompanyWatch.created_at.desc()).all())
    return [WatchResponse.model_validate(w) for w in rows]


@router.post("", response_model=WatchResponse, status_code=status.HTTP_201_CREATED)
def subscribe(body: WatchCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    watch = create_watch(db, user_id=user.id, company_id=body.company_id,
                         country=body.country, source_type=body.source_type)
    return WatchResponse.model_validate(watch)


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(watch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_watch(db, user_id=user.id, watch_id=watch_id)
