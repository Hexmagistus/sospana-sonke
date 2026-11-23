"""People asking to join the Gauteng Hustle Run closed test on Google Play.

The Android game is only installable by emails on the Play Console tester
list. A visitor who sees "not available to you" leaves their Google account
email here; an admin exports the pending emails, pastes them into Play
Console, then marks them added. No email is ever sent from this table.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class GameTesterRequest(UUIDMixin, Base):
    __tablename__ = "game_tester_requests"

    # Stored lower-cased and trimmed; unique on lower(email) as well.
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # pending | added
    status: Mapped[str] = mapped_column(String(12), server_default="pending", default="pending", nullable=False)
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ux_game_tester_requests_email_lower", func.lower(email), unique=True),
        Index("ix_game_tester_requests_status_created", "status", "created_at"),
    )
