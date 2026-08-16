"""Interview preparation model (blueprint Phase 2).

Generated from a match: likely questions, talking points (from the match reasons),
watch-outs (from the gaps), and general tips. Truthful — built from real match data.
"""
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class InterviewPrep(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "interview_preps"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("candidate_matches.id", ondelete="SET NULL"), nullable=True
    )
    vacancy_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(20), default="deterministic", nullable=False)
