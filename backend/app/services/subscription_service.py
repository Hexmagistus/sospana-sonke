"""Subscription bookkeeping and webhook handling.

Sospana Sonke is free forever -- subscriptions were permanently removed as a
gate on 2026-09-12; nothing in the product checks payment status to decide
access anymore. What remains here is: (1) the Subscription/Payment ledger,
kept so admin analytics can still report on historical revenue, and (2) the
webhook handler, which donations also route through (see the `DON-`
reference check in handle_webhook) and whose URL is configured directly in
the Paystack dashboard -- so the route and this module stay in place even
though nothing can enrol in a new subscription anymore (see
routes_subscription.py, where checkout/mock-pay/cancel now return 410).

Deterministic and idempotent. Webhook handling is keyed on the provider
reference so replays don't double-charge or double-extend (blueprint section 26).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status as http
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subscription import Subscription, Payment
from app.models.user import User
from app.payments import get_payment_provider
from app.payments.base import PaymentEvent


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite may return naive datetimes; treat stored times as UTC for comparison."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_or_create_subscription(db: Session, user_id: str) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub is not None:
        return sub
    now = _now()
    if settings.TRIAL_DAYS > 0:
        sub = Subscription(user_id=user_id, status="TRIAL",
                           trial_end=now + timedelta(days=settings.TRIAL_DAYS))
    else:
        sub = Subscription(user_id=user_id, status="EXPIRED")
    sub.provider = settings.PAYMENT_PROVIDER
    sub.amount_zar = settings.PLAN_AMOUNT_ZAR
    sub.currency = settings.PLAN_CURRENCY
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def has_active_access(sub: Subscription) -> bool:
    """Always True: Sospana Sonke is free forever, for every account,
    regardless of subscription status. `sub` is accepted (and unused) so
    existing call sites don't need to change; kept as a function rather than
    inlined `True` so a single place documents the decision."""
    return True


# ---- state transitions (idempotent) ----------------------------------------
# No new subscription can be started (see routes_subscription.py), but these
# stay in place to process any subscription-shaped event a webhook replay
# might still deliver, without special-casing it away from the payment ledger.

def _record_payment(db, sub, user_id, reference, amount, status_str, raw, provider_name) -> bool:
    """Record a payment; return False if this reference was already processed."""
    existing = (db.query(Payment)
                .filter(Payment.provider == provider_name, Payment.provider_reference == reference)
                .first())
    if existing:
        return False
    db.add(Payment(user_id=user_id, subscription_id=sub.id, provider=provider_name,
                   provider_reference=reference, amount_zar=amount or sub.amount_zar,
                   currency=sub.currency, status=status_str, raw_event=raw))
    return True


def apply_charge_success(db: Session, sub: Subscription, reference: str,
                         amount: int | None, raw: dict | None, provider_name: str) -> Subscription:
    is_new = _record_payment(db, sub, sub.user_id, reference, amount, "success", raw, provider_name)
    if is_new:
        base = _aware(sub.current_period_end)
        start = base if (base and base > _now()) else _now()
        sub.current_period_end = start + timedelta(days=settings.BILLING_PERIOD_DAYS)
        sub.status = "ACTIVE"
        sub.cancel_at_period_end = False
    db.commit()
    db.refresh(sub)
    return sub


def apply_payment_failed(db: Session, sub: Subscription, reference: str,
                         amount: int | None, raw: dict | None, provider_name: str) -> Subscription:
    _record_payment(db, sub, sub.user_id, reference or f"failed-{uuid.uuid4().hex[:8]}",
                    amount, "failed", raw, provider_name)
    sub.status = "PAST_DUE"
    db.commit()
    db.refresh(sub)
    return sub


def apply_cancelled(db: Session, sub: Subscription) -> Subscription:
    sub.status = "CANCELLED"
    db.commit()
    db.refresh(sub)
    return sub


def handle_webhook(db: Session, raw_body: bytes, signature: str | None) -> dict:
    provider = get_payment_provider()
    if not provider.verify_webhook(raw_body, signature):
        raise HTTPException(status_code=http.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature.")
    event: PaymentEvent = provider.parse_event(raw_body)
    if event.type == "ignored":
        return {"handled": False, "reason": "ignored event type"}

    # Donations share this same Paystack account/webhook endpoint but aren't
    # tied to a user subscription -- their references are prefixed `DON-` so
    # they can be routed to the separate donation ledger instead.
    if event.reference and event.reference.startswith("DON-"):
        from app.services.donation_service import handle_donation_event
        return handle_donation_event(db, event)

    sub = None
    if event.customer_email:
        user = db.query(User).filter(User.email == event.customer_email.lower()).first()
        if user:
            sub = get_or_create_subscription(db, user.id)
    if sub is None and event.reference:
        sub = db.query(Subscription).filter(Subscription.last_checkout_ref == event.reference).first()
    if sub is None:
        return {"handled": False, "reason": "no matching subscription"}

    if event.type == "charge_success":
        apply_charge_success(db, sub, event.reference or f"chg-{uuid.uuid4().hex[:8]}",
                             event.amount_zar, event.raw, provider.name)
    elif event.type == "payment_failed":
        apply_payment_failed(db, sub, event.reference, event.amount_zar, event.raw, provider.name)
    elif event.type == "subscription_cancelled":
        apply_cancelled(db, sub)
    return {"handled": True, "type": event.type, "status": sub.status}
