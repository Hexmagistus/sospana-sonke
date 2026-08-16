"""Mock payment provider for development and tests (no network).

Produces a fake checkout URL and signs webhooks with HMAC-SHA256 over a static
dev secret so the webhook path can be exercised offline. NEVER use in production —
the factory only selects it when PAYMENT_PROVIDER=mock.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from app.payments.base import PaymentProvider, CheckoutSession, PaymentEvent

_MOCK_SECRET = b"mock-dev-secret"


class MockProvider(PaymentProvider):
    name = "mock"

    def start_checkout(self, *, email, amount_zar, reference, metadata) -> CheckoutSession:
        return CheckoutSession(
            authorization_url=f"https://mock-pay.local/checkout/{reference}",
            reference=reference,
        )

    @staticmethod
    def sign(raw_body: bytes) -> str:
        return hmac.new(_MOCK_SECRET, raw_body, hashlib.sha256).hexdigest()

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        return bool(signature) and hmac.compare_digest(self.sign(raw_body), signature)

    def parse_event(self, raw_body: bytes) -> PaymentEvent:
        body = json.loads(raw_body.decode() or "{}")
        return PaymentEvent(
            type=body.get("type", "ignored"),
            reference=body.get("reference"),
            customer_email=body.get("email"),
            amount_zar=body.get("amount_zar"),
            raw=body,
        )
