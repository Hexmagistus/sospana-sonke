"""Donation routes -- one-off support to help keep Sospana Sonke free.

No login required: anyone can donate. Kept separate from /subscription.
Cash send never stores a card or bank account: the page only shows a cellphone
number from configuration so the donor can pay inside their own bank app.
"""
import re

from app.core.config import settings
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.donation import DonationCheckoutRequest, DonationCheckoutResponse
from app.services import donation_service

router = APIRouter(prefix="/donations", tags=["donations"])

_PHONE = re.compile(r"^\+?[0-9]{8,15}$")
_REFERENCE = "Sospana Sonke donation"


@router.get("/cashsend")
@limiter.limit("30/minute")
def cashsend(request: Request):
    """Whether a cash-send number is published. The number is for donors to type
    into their own bank app. It is not a credential, and we do not record who asked."""
    raw = (settings.DONATION_CASHSEND_NUMBER or "").strip().replace(" ", "").replace("-", "")
    if not _PHONE.match(raw):
        return {"ready": False, "number": None, "reference": _REFERENCE}
    return {"ready": True, "number": raw, "reference": _REFERENCE}


@router.post("/checkout", response_model=DonationCheckoutResponse)
@limiter.limit("10/hour")
def checkout(request: Request, body: DonationCheckoutRequest, db: Session = Depends(get_db)):
    # With no real payment provider configured, production would hand donors a
    # dead mock checkout link and store an unpayable pending row per click.
    if settings.ENV == "production" and settings.PAYMENT_PROVIDER == "mock":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Our card machine is still on its way (card donations aren't live yet). Cash send works when a number is published on this page. Thank you!")
    try:
        result = donation_service.start_checkout(
            db, amount_zar=body.amount_zar, email=body.email,
            name=body.name, message=body.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return DonationCheckoutResponse(**result)
