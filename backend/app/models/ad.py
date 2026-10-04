"""Advertiser spot applications for the explorer pages.

An application is only a request. Nothing here takes a payment, sends an email
or publishes anything: an administrator reads the application, sets the status
and (for an approval) the slot, and only an `approved` row inside its date
window is returned by the public slots endpoint. No ads are seeded.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class AdApplication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ad_applications"

    business_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(254), index=True, nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    ad_text: Mapped[str] = mapped_column(String(120), nullable=False)
    # What the advertiser chose to give per day, in US dollars. At least 1.00.
    amount_usd_per_day: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    # Spot the advertiser asked for, e.g. "L3" or "R7". The admin may assign another.
    requested_slot: Mapped[str | None] = mapped_column(String(4), nullable=True)
    # pending | approved | rejected
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True, nullable=False)
    # The slot an approved ad is shown in, and its run window (set on approval).
    slot_key: Mapped[str | None] = mapped_column(String(4), index=True, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
