"""Crowd-sourced "report a broken link" model.

Most rows imported via the seed CSV are `scraping_status = "pending"` --
cross-checked by web search when added, never fetched live from here. Rather
than wait for the periodic re-check (app/services/link_check_service.py) or
an admin's manual URL test to catch a dead or wrong link, any signed-in
candidate can flag one directly; this is that report, triaged by an admin.
"""
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class LinkReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "link_reports"

    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # open | reviewed | resolved -- admin-managed triage state.
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False)
