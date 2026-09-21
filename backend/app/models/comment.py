"""Community tips under an employer's careers link.

POPIA: short, filtered, first-name + last-initial only, auto-expire after 30 days,
erased with the account. Community-hidden after 3 flags; admins can restore/remove.
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin

COMMENT_TTL_DAYS = 30
COMMENT_KINDS = {"works", "broken", "open", "closed", "tip"}


class CompanyComment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "company_comments"

    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    body: Mapped[str | None] = mapped_column(String(300), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CommentFlag(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "comment_flags"
    __table_args__ = (UniqueConstraint("comment_id", "user_id", name="uq_comment_flag"),)

    comment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("company_comments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
