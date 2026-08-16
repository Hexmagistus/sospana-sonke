"""Candidate-vacancy match and system settings (blueprint sections 8, 9, 10, 17 & 34).

A CandidateMatch is the explainable output of the matching engine for one
candidate + one vacancy: an overall score, per-dimension sub-scores, whether the
hard requirements are satisfied, a decision (APPLY / REVIEW / DO_NOT_APPLY), the
human-readable reasons and gaps, and the tracking status. Scoring is deterministic
(never controlled by an LLM); the record stores which engine/model produced it.
"""
from sqlalchemy import String, Float, Boolean, Text, ForeignKey, JSON, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class CandidateMatch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidate_matches"
    __table_args__ = (UniqueConstraint("user_id", "vacancy_id", name="uq_match_user_vacancy"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="CASCADE"), index=True, nullable=False
    )

    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)          # 0-100
    sub_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    band: Mapped[str] = mapped_column(String(12), default="Reject", nullable=False)   # Strong|Good|Possible|Weak|Reject
    decision: Mapped[str] = mapped_column(String(15), default="DO_NOT_APPLY", nullable=False)
    confidence: Mapped[str] = mapped_column(String(8), default="Low", nullable=False)  # High|Medium|Low
    hard_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    reasons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    gaps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Tracking lifecycle (blueprint section 17). Matching sets MATCHED or REJECTED.
    status: Mapped[str] = mapped_column(String(30), default="MATCHED", nullable=False)

    engine_version: Mapped[str] = mapped_column(String(40), default="deterministic-v1", nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(80), nullable=True)


class SystemSetting(UUIDMixin, TimestampMixin, Base):
    """Admin-editable key/value settings (e.g. match weights & thresholds)."""
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
