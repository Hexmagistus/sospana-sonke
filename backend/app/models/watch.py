"""Notify-me subscription model (extends blueprint section 31's alerting).

A CompanyWatch lets a signed-in candidate opt into an email alert when a
careers page changes -- either one specific company/university, or more
broadly every company matching a country and/or source_type category. This
is distinct from the existing broad "new jobs" broadcast (which tells every
active candidate about newly *scraped* vacancies) and from Subscription
(billing) in app/models/subscription.py -- a watch is scoped and opt-in, and
covers companies whose careers link isn't structured-vacancy-scrapable too
(see app/services/link_check_service.py).
"""
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class CompanyWatch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "company_watches"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Scope: a specific company, OR a country/source_type combination (each
    # half optional -- None means "any"). At least one of the three must be
    # set; app/services/watch_service.create_watch enforces that.
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=True
    )
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(10), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
