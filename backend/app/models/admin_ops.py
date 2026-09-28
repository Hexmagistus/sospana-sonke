"""Admin tagging and an audit trail for those actions.

Tags exist so an administrator can group people who asked to hear about a
kind of post. They are not a marketing list: a tag may only be attached to
someone who set a preferred post and opted in to opportunity alerts.
"""
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class UserTag(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_tags"
    __table_args__ = (UniqueConstraint("user_id", "tag", name="uq_user_tag"),)

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    tag: Mapped[str] = mapped_column(String(40), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class AdminAuditLog(UUIDMixin, TimestampMixin, Base):
    """Who did what. Detail is a short note (counts, tag name), never an email dump."""

    __tablename__ = "admin_audit_log"

    admin_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    target_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail: Mapped[str] = mapped_column(String(500), nullable=False, default="")
