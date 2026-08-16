"""Subscription and payment models (blueprint sections 17 & 26).

One subscription per user, moving through TRIAL → ACTIVE → PAST_DUE → CANCELLED
/ EXPIRED. Payments are an immutable ledger keyed by the provider's reference so
webhook handling is idempotent. The payment provider is swappable (Paystack today).
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin

SUBSCRIPTION_STATUSES = ["TRIAL", "ACTIVE", "PAST_DUE", "CANCELLED", "EXPIRED"]


class Subscription(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(12), default="TRIAL", nullable=False)

    provider: Mapped[str] = mapped_column(String(20), default="mock", nullable=False)
    provider_customer_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_subscription_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_checkout_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)

    amount_zar: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ZAR", nullable=False)

    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("provider", "provider_reference", name="uq_payment_ref"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subscription_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_zar: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ZAR", nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)  # success | failed | refunded | pending
    raw_event: Mapped[dict | None] = mapped_column(JSON, nullable=True)
