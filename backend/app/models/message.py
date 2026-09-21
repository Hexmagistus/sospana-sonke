"""Temporary user-to-user messages, blocks and abuse reports.

Design (POPIA data minimisation + storage limitation):
- A message is auto-deleted 24 hours after it is sent (expires_at). Nothing is
  kept beyond that, except a snapshot copied into MessageReport when the
  recipient reports it, which admins review and which is purged after 30 days.
- Recipients are opt-in (users.allow_messages) and can block any sender.
- Email addresses and phone numbers are never exposed to other users.
"""
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin

MESSAGE_TTL_HOURS = 24
REPORT_RETENTION_DAYS = 30


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    sender_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recipient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserBlock(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),)

    blocker_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    blocked_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )


class MessageReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "message_reports"

    reporter_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Snapshot: the original message is deleted on its normal schedule.
    body_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(String(30), nullable=False)  # harassment|scam|spam|inappropriate|other
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False)  # open|dismissed|actioned
    purge_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
