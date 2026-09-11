"""Job-Aligned CV Builder: job-description analysis + application tracking.

A JobAnalysis is created whenever a candidate pastes a job advertisement into
the "Tailor my CV to a job" flow (routes_tailor.py). It is a NEW, standalone
table so it needs no change to any existing table: it holds the parsed job
requirements, the deterministic match report against the candidate's real
profile, the ATS/quality/readiness scores, links to whatever CV version /
cover letter were generated from it, and the same lifecycle fields a
scraped-vacancy Application would have — so one row doubles as both the
"Job Analysis" record and a "Job Application History" tracker row for jobs
that were never scraped (an ad, a referral, a job seen on LinkedIn, etc).

Nothing here overwrites the candidate's CandidateProfile ("Master CV") — this
table only ever reads from it (see app/services/job_analysis_service.py).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import String, Float, Boolean, Text, Date, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin

# Application-tracker lifecycle (blueprint: Job Application History tracker).
JOB_APPLICATION_STATUSES = [
    "PREPARING", "APPLIED", "INTERVIEW", "ASSESSMENT", "OFFER", "REJECTED", "WITHDRAWN",
]


class JobAnalysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "job_analyses"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # What the candidate gave us — never altered once saved, so re-opening this
    # analysis always reflects the actual job advert that was pasted.
    job_title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ---- Job-description analysis (parser output) ---------------------------
    # {seniority, keywords: {category: [terms]}, action_verbs: [...],
    #  requirements: [{text, kind, category}], requirement_counts: {...}}
    extracted: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # ---- CV ↔ job match report (deterministic matching engine) --------------
    match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sub_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    band: Mapped[str] = mapped_column(String(12), default="Reject", nullable=False)
    decision: Mapped[str] = mapped_column(String(15), default="DO_NOT_APPLY", nullable=False)
    confidence: Mapped[str] = mapped_column(String(8), default="Low", nullable=False)
    hard_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Strong Matches / Partial Matches / Missing Requirements — each a list of
    # {"text": <requirement text>, "note": <explanatory narrative>}. Missing
    # requirements are always phrased "not found in your CV", never "you don't
    # have this" (blueprint: never assert absence of a skill/qualification the
    # candidate simply didn't mention).
    strong_matches: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    partial_matches: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missing_requirements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # ---- ATS optimisation score ----------------------------------------------
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ats_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ---- CV quality score -----------------------------------------------------
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quality_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ---- Application Readiness dashboard --------------------------------------
    readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readiness_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Generated documents (nullable until the candidate generates them) ----
    template: Mapped[str] = mapped_column(String(20), default="professional", nullable=False)
    cv_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cv_versions.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True
    )

    # ---- Job Application History tracker fields -------------------------------
    status: Mapped[str] = mapped_column(String(15), default="PREPARING", nullable=False)
    date_applied: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
