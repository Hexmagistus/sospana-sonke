"""Subscription & payment routes (blueprint Steps 9, sections 17 & 26).

Sospana Sonke is free forever: subscriptions have been permanently removed,
so checkout/cancel/mock-pay are gone (410 Gone) -- there is nothing left to
buy or cancel. GET still reports the account's (now purely historical)
subscription record, with has_access always true. The webhook route stays
exactly as-is: its URL is configured directly in the Paystack dashboard, and
donations are routed through the same handler (see subscription_service's
module docstring).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_service import (
    get_or_create_subscription, has_active_access, handle_webhook,
)

router = APIRouter(prefix="/subscription", tags=["subscription"])

_REMOVED = "Sospana Sonke is free forever -- subscriptions have been permanently removed."


def _to_response(sub) -> SubscriptionResponse:
    return SubscriptionResponse(
        status=sub.status, has_access=has_active_access(sub), provider=sub.provider,
        amount_zar=sub.amount_zar, currency=sub.currency, trial_end=sub.trial_end,
        current_period_end=sub.current_period_end, cancel_at_period_end=sub.cancel_at_period_end,
    )


@router.get("", response_model=SubscriptionResponse)
def get_subscription(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _to_response(get_or_create_subscription(db, user.id))


@router.post("/checkout")
def checkout():
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_REMOVED)


@router.post("/cancel")
def cancel():
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_REMOVED)


@router.post("/mock-pay")
def mock_pay():
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_REMOVED)


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Payment-provider webhook. Body signature is verified before processing.
    Kept working for donations, which route through the same handler; see
    subscription_service.handle_webhook."""
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature") or request.headers.get("x-signature")
    return handle_webhook(db, raw, signature)
