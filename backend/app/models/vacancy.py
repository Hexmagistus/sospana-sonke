"""Vacancy discovery models (blueprint sections 5, 6, 7, 9 & 23).

A company can have one or more VacancySources (careers pages / ATS endpoints).
Each scan of a source yields Vacancies, which carry both the structured fields and
the original raw content, plus a content hash for deduplication. Requirements are
split into hard vs soft (section 9). Change-detection state lives on the source.
"""
from datetime import datetime, date

from sqlalchemy import String, Integer, Text, Boolean, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin


class VacancySource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vacancy_sources"

    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # greenhouse | lever | smartrecruiters | static | pdf | unknown
    ats_type: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # e.g. board token
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Politeness / change detection
    robots_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    # pending | ok | empty | http_error | parse_error | robots_disallowed | structure_changed
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_vacancy_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    vacancies: Mapped[list["Vacancy"]] = relationship(back_populates="source")


class Vacancy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vacancies"

    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vacancy_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )

    external_id: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)  # employer vacancy id
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)   # remote|hybrid|onsite
    employment_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    salary: Mapped[str | None] = mapped_column(String(120), nullable=True)
    posting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Original advertisement content, retained for re-analysis (section 6).
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Lifecycle / change detection
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped["VacancySource"] = relationship(back_populates="vacancies")
    requirements: Mapped[list["VacancyRequirement"]] = relationship(
        back_populates="vacancy", cascade="all, delete-orphan"
    )


class VacancyRequirement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vacancy_requirements"

    vacancy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), default="soft", nullable=False)   # hard | soft
    # qualification | experience | certification | registration | licence | skill | other
    category: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    extracted_by: Mapped[str] = mapped_column(String(10), default="rules", nullable=False)  # rules | ai

    vacancy: Mapped["Vacancy"] = relationship(back_populates="requirements")
