"""Payment provider interface.

All providers expose the same three operations so the rest of the app never
depends on a specific vendor: start a checkout, verify a webhook signature, and
parse a webhook body into a normalised PaymentEvent.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CheckoutSession:
    authorization_url: str
    reference: str


@dataclass
class PaymentEvent:
    # Normalised event type: charge_success | payment_failed | subscription_cancelled | ignored
    type: str
    reference: str | None = None
    customer_email: str | None = None
    amount_zar: int | None = None
    subscription_ref: str | None = None
    raw: dict | None = None


class PaymentProvider(ABC):
    name: str = "base"

    @abstractmethod
    def start_checkout(self, *, email: str, amount_zar: int, reference: str,
                       metadata: dict) -> CheckoutSession: ...

    @abstractmethod
    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool: ...

    @abstractmethod
    def parse_event(self, raw_body: bytes) -> PaymentEvent: ...
