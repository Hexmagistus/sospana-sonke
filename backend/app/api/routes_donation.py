"""Donation routes -- one-off support to help keep Sospana Sonke free.

No login required: anyone can donate. Kept separate from /subscription.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.donation import DonationCheckoutRequest, DonationCheckoutResponse
from app.services import donation_service

router = APIRouter(prefix="/donations", tags=["donations"])


@router.post("/checkout", response_model=DonationCheckoutResponse)
@limiter.limit("10/hour")
def checkout(request: Request, body: DonationCheckoutRequest, db: Session = Depends(get_db)):
    try:
        result = donation_service.start_checkout(
            db, amount_zar=body.amount_zar, email=body.email,
            name=body.name, message=body.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return DonationCheckoutResponse(**result)
