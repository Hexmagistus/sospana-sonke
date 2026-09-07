"""One-off donation checkout + webhook handling.

Donations are a voluntary way for anyone (logged in or not) to help keep
Sospana Sonke free for jobseekers. They deliberately don't touch the
Subscription/access-gating machinery in subscription_service. They reuse the
same Paystack account and webhook endpoint as subscriptions -- donation
references are prefixed `DON-` so subscription_service.handle_webhook can
route donation events here (see that module for the dispatch).
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.donation import Donation
from app.payments import get_payment_provider
from app.payments.base import PaymentEvent

MIN_AMOUNT_ZAR = 5
MAX_AMOUNT_ZAR = 20000
SUGGESTED_AMOUNTS_ZAR = [20, 50, 100]


def start_checkout(db: Session, *, amount_zar: int, email: str,
                   name: str | None = None, message: str | None = None) -> dict:
    if amount_zar < MIN_AMOUNT_ZAR or amount_zar > MAX_AMOUNT_ZAR:
        raise ValueError(f"Amount must be between R{MIN_AMOUNT_ZAR} and R{MAX_AMOUNT_ZAR}.")

    provider = get_payment_provider()
    reference = f"DON-{uuid.uuid4().hex[:12]}"
    donation = Donation(
        donor_name=name, donor_email=email.lower(), message=message,
        amount_zar=amount_zar, currency=settings.PLAN_CURRENCY,
        provider=provider.name, provider_reference=reference, status="pending",
    )
    db.add(donation)
    db.commit()

    session = provider.start_checkout(
        email=email, amount_zar=amount_zar, reference=reference,
        metadata={"kind": "donation", "donor_name": name},
        callback_url=settings.DONATION_RETURN_URL,
    )
    # Paystack echoes back the same reference we sent, but keep this in sync
    # with whatever the provider actually settled on.
    donation.provider_reference = session.reference
    db.commit()
    return {"authorization_url": session.authorization_url, "reference": session.reference}


def handle_donation_event(db: Session, event: PaymentEvent) -> dict:
    donation = (db.query(Donation)
               .filter(Donation.provider_reference == event.reference)
               .first())
    if donation is None:
        return {"handled": False, "reason": "no matching donation"}

    if event.type == "charge_success":
        if donation.status != "success":  # idempotent against webhook replays
            donation.status = "success"
            donation.raw_event = event.raw
            if event.amount_zar:
                donation.amount_zar = event.amount_zar
            db.commit()
        return {"handled": True, "type": "donation_success", "status": donation.status}

    if event.type == "payment_failed":
        donation.status = "failed"
        donation.raw_event = event.raw
        db.commit()
        return {"handled": True, "type": "donation_failed", "status": donation.status}

    return {"handled": False, "reason": "unhandled event type for donation"}
