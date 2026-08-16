"""Application tracking models (blueprint sections 13-17, 30).

Application ties a candidate + vacancy + generated documents together and moves
through the status lifecycle. ApplicationAnswer records each form answer and its
source (from-profile vs candidate-entered vs AI-generated), never fabricating
facts. ApplicationEvent is the immutable audit trail. ApplicationSettings holds
the candidate's autonomy mode, anti-spam caps, and exclusions.
"""
from datetime import datetime

from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

# Status lifecycle (blueprint section 17).
STATUSES = [
    "DISCOVERED", "ANALYZING", "MATCHED", "REJECTED", "CV_CREATED", "APPLICATION_PREPARED",
    "AWAITING_APPROVAL", "SUBMITTED", "APPLICATION_FAILED", "CANDIDATE_ACTION_REQUIRED",
    "INTERVIEW", "REJECTED_BY_EMPLOYER", "WITHDRAWN", "OFFER", "CLOSED",
]
# Statuses a candidate may set directly once an application exists.
CANDIDATE_SETTABLE = {"INTERVIEW", "REJECTED_BY_EMPLOYER", "WITHDRAWN", "OFFER", "CLOSED"}


class ApplicationSettings(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_settings"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    application_mode: Mapped[str] = mapped_column(String(12), default="approval", nullable=False)
    # automatic | approval | assisted
    auto_apply_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_match_score: Mapped[float] = mapped_column(default=70.0, nullable=False)
    max_applications_per_day: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_applications_per_week: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    excluded_companies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    excluded_roles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "vacancy_id", name="uq_app_user_vacancy"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("candidate_matches.id", ondelete="SET NULL"), nullable=True
    )
    cv_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cv_versions.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True
    )

    mode: Mapped[str] = mapped_column(String(12), default="approval", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="APPLICATION_PREPARED", nullable=False)
    submission_method: Mapped[str | None] = mapped_column(String(12), nullable=True)  # auto|assisted|manual
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_required_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    answers: Mapped[list["ApplicationAnswer"]] = relationship(
        back_populates="application", cascade="all, delete-orphan")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application", cascade="all, delete-orphan")


class ApplicationAnswer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_answers"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # profile | candidate | ai_generated
    source: Mapped[str] = mapped_column(String(15), default="profile", nullable=False)
    is_unknown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="answers")


class ApplicationEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_events"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status_from: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status_to: Mapped[str | None] = mapped_column(String(30), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(20), default="system", nullable=False)  # system|candidate

    application: Mapped["Application"] = relationship(back_populates="events")
