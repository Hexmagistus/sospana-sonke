"""Generated-document models (blueprint sections 11, 12, 32 & 33).

Tailored CV versions and cover letters are stored separately from the original
uploaded CV (which is never overwritten). Each version records the rendered
PDF/DOCX storage keys, the ATS compatibility score, and whether it passed the
truthfulness validation (every claim must be backed by the candidate's profile).
"""
from sqlalchemy import String, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class CVVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cv_versions"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("candidate_matches.id", ondelete="SET NULL"), nullable=True
    )
    vacancy_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True
    )
    source_cv_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )

    label: Mapped[str] = mapped_column(String(300), nullable=False)  # human filename
    template: Mapped[str] = mapped_column(String(40), default="ats_clean", nullable=False)

    content: Mapped[dict] = mapped_column(JSON, nullable=False)       # the structured CV data used
    storage_key_pdf: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_key_docx: Mapped[str | None] = mapped_column(String(512), nullable=True)

    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ats_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    truthfulness_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    truthfulness_violations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    generated_by: Mapped[str] = mapped_column(String(20), default="deterministic", nullable=False)


class CoverLetter(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cover_letters"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("candidate_matches.id", ondelete="SET NULL"), nullable=True
    )
    vacancy_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True
    )

    label: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key_pdf: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_key_docx: Mapped[str | None] = mapped_column(String(512), nullable=True)

    truthfulness_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(20), default="deterministic", nullable=False)
