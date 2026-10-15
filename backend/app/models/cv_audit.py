"""ATS CV Audit ("CV Doctor") results.

One row per audit run over one of the candidate's uploaded CVs. The uploaded
original is never modified (cvs.is_original stays the source of truth); this
row holds the audit findings, the before/after scores, the rebuilt CV content
the candidate can edit, the stress-test results, the outstanding-information
checklist and career directions. DOCX/PDF/report files are rendered on demand
from ``rebuilt`` so an edit never leaves a stale file behind.
"""
from __future__ import annotations

from sqlalchemy import String, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class CVAudit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cv_audits"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    cv_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cvs.id", ondelete="CASCADE"), index=True, nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # Phase 1 — the original document.
    document_facts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    findings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    parsed: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    original_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Phase 2-4 — the rebuilt CV (editable by the candidate) and what changed.
    rebuilt: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    change_log: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    edited_by_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Phase 5 — stress test on the generated files, and the final scores.
    stress: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    final_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    compact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Deliverables 3/4 and Phase 7.
    limitations: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    checklist: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    directions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
