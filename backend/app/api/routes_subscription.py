"""Subscription & payment routes (blueprint Steps 9, sections 17 & 26)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse, CheckoutResponse
from app.services.subscription_service import (
    get_or_create_subscription, has_active_access, start_checkout, cancel_subscription,
    handle_webhook, apply_charge_success,
)

router = APIRouter(prefix="/subscription", tags=["subscription"])


def _to_response(sub) -> SubscriptionResponse:
    return SubscriptionResponse(
        status=sub.status, has_access=has_active_access(sub), provider=sub.provider,
        amount_zar=sub.amount_zar, currency=sub.currency, trial_end=sub.trial_end,
        current_period_end=sub.current_period_end, cancel_at_period_end=sub.cancel_at_period_end,
    )


@router.get("", response_model=SubscriptionResponse)
def get_subscription(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _to_response(get_or_create_subscription(db, user.id))


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return CheckoutResponse(**start_checkout(db, user))


@router.post("/cancel", response_model=SubscriptionResponse)
def cancel(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _to_response(cancel_subscription(db, user))


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Payment-provider webhook. Body signature is verified before processing."""
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature") or request.headers.get("x-signature")
    return handle_webhook(db, raw, signature)


@router.post("/mock-pay", response_model=SubscriptionResponse)
def mock_pay(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Development-only shortcut to simulate a successful payment (mock provider)."""
    if settings.PAYMENT_PROVIDER != "mock":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available.")
    sub = get_or_create_subscription(db, user.id)
    reference = f"MOCK-{uuid.uuid4().hex[:12]}"
    apply_charge_success(db, sub, reference, sub.amount_zar,
                         {"simulated": True}, provider_name="mock")
    return _to_response(sub)
