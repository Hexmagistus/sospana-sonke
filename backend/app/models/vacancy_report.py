"""Crowd-sourced "report this opportunity" model (trust & safety, blueprint section 18).

Distinct from `LinkReport` (a company's careers-page link being broken/wrong) --
this is a candidate flagging a *specific vacancy listing itself* as a scam,
expired, incorrect, duplicate, or misleading, mirroring the same reported-by-
candidate / triaged-by-admin pattern already established for link reports.
"""
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin

# Fixed, closed set -- kept in sync with the frontend's report dialog. "other"
# always requires `details` to be useful to an admin triaging the queue.
VACANCY_REPORT_CATEGORIES = ["scam", "expired", "incorrect", "duplicate", "misleading", "other"]


class VacancyReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vacancy_reports"

    vacancy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    # open | reviewed | resolved -- admin-managed triage state, same convention as LinkReport.
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False)
