"""One row per user per calendar day (South Africa time) for the daily digest.

The UNIQUE (user_id, digest_date) constraint is the idempotency guard: a row is
inserted ("claimed") before the email is handed to the provider, so a second
cron call, a retry or two overlapping workers cannot send a second digest for
the same day. A definite send failure deletes the claim so the user is retried;
a claim left behind by a crash simply means that user waits until tomorrow
(safe direction: no duplicates).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class DigestLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "digest_log"
    __table_args__ = (UniqueConstraint("user_id", "digest_date", name="uq_digest_user_day"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    digest_date: Mapped[str] = mapped_column(String(10), nullable=False)   # YYYY-MM-DD, SAST
    status: Mapped[str] = mapped_column(String(10), default="claimed", nullable=False)  # claimed | sent
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
