"""Donation model — one-off, voluntary contributions to keep Sospana Sonke free.

Donations are deliberately separate from the Subscription/Payment ledger
(sections 17 & 26): they aren't tied to a user account or access gating, and
anyone can donate without logging in. Kept as an immutable-ish ledger keyed by
the provider's reference so webhook replays don't double-count (same idempotency
pattern as Payment).
"""
from sqlalchemy import String, Integer, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin

DONATION_STATUSES = ["pending", "success", "failed"]


class Donation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "donations"
    __table_args__ = (UniqueConstraint("provider", "provider_reference", name="uq_donation_ref"),)

    donor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    donor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    amount_zar: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ZAR", nullable=False)

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="pending", nullable=False)
    raw_event: Mapped[dict | None] = mapped_column(JSON, nullable=True)
