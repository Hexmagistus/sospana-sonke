"""Candidate report model (blueprint section 18).

A Report is a point-in-time snapshot of a candidate's job-search cycle — vacancies
analysed, qualified, rejected, CVs and cover letters generated, applications
submitted and awaiting action — rendered to a downloadable PDF.
"""
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class Report(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    stats: Mapped[dict] = mapped_column(JSON, nullable=False)
    storage_key_pdf: Mapped[str | None] = mapped_column(String(512), nullable=True)
