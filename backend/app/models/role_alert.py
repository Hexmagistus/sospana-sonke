"""A saved daily-role alert: country, category, and keyword.

This is a separate choice from ``notify_opportunity_alerts`` (an administrator
may email the person about a named post) and from ``CompanyWatch`` (a careers
page changed). A row here means the person asked for the existing daily digest
to list only new stored roles that match. At least one of country, category,
and keyword is set. An unset field means any value.
"""
from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class RoleAlert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "role_alerts"
    __table_args__ = (
        Index("ix_role_alerts_user_active", "user_id", "active"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)
    category: Mapped[str | None] = mapped_column(String(10), nullable=True)
    keyword: Mapped[str | None] = mapped_column(String(80), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
