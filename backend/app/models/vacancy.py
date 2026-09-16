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

    # Structured, best-effort filter fields derived from the free-text fields above
    # at scan time (see app.scraper.extract). Additive only — location/salary above
    # remain the source of truth shown to a candidate; these three just let the API
    # facet/filter without needing a candidate to parse prose. All nullable: a None
    # means "couldn't be inferred", never a fabricated value.
    province: Mapped[str | None] = mapped_column(String(40), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # monthly ZAR
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)  # monthly ZAR
    nqf_level: Mapped[int | None] = mapped_column(Integer, nullable=True)   # estimated, 1-10

    # Trust & safety (blueprint section 18): heuristic scam/quality signals computed
    # at scan time (app.services.trust_service), e.g. ["payment_request"]. Never
    # hidden from admins/candidates -- shown as flags to be aware of, not a verdict.
    trust_flags: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    # Duplicate detection (blueprint section 16): set when an admin merges this
    # vacancy into another (the canonical one keeps this null). The merged row is
    # also soft-deleted (deleted_at) and closed (is_open=False), never hard-deleted.
    duplicate_of_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True
    )

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
