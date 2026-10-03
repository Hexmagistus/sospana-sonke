"""One row per careers-page scan. No candidate or admin identity is stored."""
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class ScanLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scan_logs"

    company_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vacancy_sources.id", ondelete="SET NULL"), nullable=True
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pages_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vacancies_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vacancies_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vacancies_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_prevented: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vacancies_closed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parser_used: Mapped[str | None] = mapped_column(String(40), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
