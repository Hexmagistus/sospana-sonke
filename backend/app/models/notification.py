"""Notification and scheduled-job-run models (blueprint sections 22, 31 & 43).

Notification is a per-candidate message shown on the dashboard (and optionally
emailed). JobRun is the observability log for the scheduler so an administrator
can see when each recurring job last ran and whether it succeeded.
"""
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # strong_match | action_required | report_ready | system
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Link back to the thing that triggered it (for idempotency + deep-linking).
    related_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    related_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PushToken(UUIDMixin, TimestampMixin, Base):
    """A candidate's registered device token for push notifications."""
    __tablename__ = "push_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), default="web", nullable=False)


class JobRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "job_runs"

    job_name: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="success", nullable=False)  # success | error
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
