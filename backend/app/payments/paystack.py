"""Paystack payment provider (blueprint sections 17 & 26).

Uses Paystack's Transaction Initialize endpoint for checkout and verifies webhooks
with an HMAC-SHA512 signature over the raw request body (the `x-paystack-signature`
header), exactly as Paystack documents. Amounts are sent in kobo/cents (×100).
"""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx

from app.core.config import settings
from app.payments.base import PaymentProvider, CheckoutSession, PaymentEvent


class PaystackProvider(PaymentProvider):
    name = "paystack"

    def __init__(self) -> None:
        if not settings.PAYSTACK_SECRET_KEY:
            raise RuntimeError("PAYSTACK_SECRET_KEY is not configured.")
        self._secret = settings.PAYSTACK_SECRET_KEY

    def start_checkout(self, *, email, amount_zar, reference, metadata) -> CheckoutSession:
        resp = httpx.post(
            "https://api.paystack.co/transaction/initialize",
            headers={"Authorization": f"Bearer {self._secret}", "Content-Type": "application/json"},
            json={"email": email, "amount": amount_zar * 100, "currency": settings.PLAN_CURRENCY,
                  "reference": reference, "callback_url": settings.PAYMENT_CALLBACK_URL,
                  "metadata": metadata},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return CheckoutSession(authorization_url=data["authorization_url"], reference=data["reference"])

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        expected = hmac.new(self._secret.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_event(self, raw_body: bytes) -> PaymentEvent:
        body = json.loads(raw_body.decode() or "{}")
        event = body.get("event", "")
        data = body.get("data", {})
        customer = (data.get("customer") or {}).get("email")
        reference = data.get("reference")
        amount = int(data.get("amount", 0)) // 100 if data.get("amount") else None
        if event == "charge.success":
            return PaymentEvent("charge_success", reference, customer, amount, raw=body)
        if event in ("invoice.payment_failed", "charge.failed"):
            return PaymentEvent("payment_failed", reference, customer, amount, raw=body)
        if event in ("subscription.disable", "subscription.not_renew"):
            return PaymentEvent("subscription_cancelled", reference, customer, amount, raw=body)
        return PaymentEvent("ignored", reference, customer, amount, raw=body)
