"""Dashboard aggregation (blueprint sections 19, 21 & 44).

Read-only aggregate queries for the candidate dashboard and the admin/business
dashboard. All figures are computed deterministically from the database.
"""
from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application
from app.models.company import Company
from app.models.document import CVVersion, CoverLetter
from app.models.match import CandidateMatch
from app.models.profile import CandidateProfile, Education, Skill, WorkExperience
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource

_STRONG_BANDS = ("Strong", "Good")
_AWAITING = ("AWAITING_APPROVAL", "CANDIDATE_ACTION_REQUIRED")


def _profile_nudge(db: Session, user: User) -> str | None:
    """A one-line, personalized banner nudging a candidate to finish their
    profile -- referencing the "Preferred post" / "Name of qualification"
    answers they already gave at registration, so it reads as a callback to
    something they told us rather than a generic nag. Only returns a nudge
    when there's something real to reference (registration left at least one
    of those two fields filled in) AND the candidate hasn't already engaged
    with their profile (no confirmed education, skill, or work-experience
    record) -- once they have, this stops showing.
    """
    if not (user.preferred_position or user.qualification_name):
        return None

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    if profile is not None:
        has_confirmed = (
            db.query(Education.id).filter(Education.profile_id == profile.id,
                                          Education.confirmed_by_candidate.is_(True)).first()
            or db.query(Skill.id).filter(Skill.profile_id == profile.id).first()
            or db.query(WorkExperience.id).filter(WorkExperience.profile_id == profile.id).first()
        )
        if has_confirmed:
            return None

    if user.preferred_position and user.qualification_name:
        return (f"You told us you're aiming for a {user.preferred_position} role with your "
                f"{user.qualification_name} -- complete your profile so we can match you more precisely.")
    if user.preferred_position:
        return (f"You told us you're aiming for a {user.preferred_position} role -- "
                f"complete your profile so we can match you more precisely.")
    return (f"You told us about your {user.qualification_name} -- "
            f"complete your profile so we can match you more precisely.")


def _as_int(value) -> int:
    return int(value or 0)


def candidate_dashboard(db: Session, user: User) -> dict:
    # No subscription fields here -- Sospana Sonke is free forever, so a
    # candidate's dashboard has nothing to report about billing.
    #
    # Counts that used to be one SELECT each are folded into a single aggregate
    # per table, so a dashboard view is a handful of round trips instead of ~12.

    match_total, strong, apply_n = db.query(
        func.count(CandidateMatch.id),
        func.coalesce(func.sum(case((CandidateMatch.band.in_(tuple(_STRONG_BANDS)), 1), else_=0)), 0),
        func.coalesce(func.sum(case((CandidateMatch.decision == "APPLY", 1), else_=0)), 0),
    ).filter(CandidateMatch.user_id == user.id).one()

    app_total, submitted, awaiting, interviews, offers = db.query(
        func.count(Application.id),
        func.coalesce(func.sum(case((Application.status == "SUBMITTED", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Application.status.in_(tuple(_AWAITING)), 1), else_=0)), 0),
        func.coalesce(func.sum(case((Application.status == "INTERVIEW", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Application.status == "OFFER", 1), else_=0)), 0),
    ).filter(Application.user_id == user.id).one()

    open_n, listings_updated_at = db.query(
        func.count(Vacancy.id),
        func.max(Vacancy.last_seen_at),
    ).filter(Vacancy.is_open.is_(True)).one()

    return {
        "vacancies_open": _as_int(open_n),
        "total_matches": _as_int(match_total),
        "strong_matches": _as_int(strong),
        "apply_matches": _as_int(apply_n),
        "cvs_generated": _as_int(
            db.query(func.count(CVVersion.id)).filter(CVVersion.user_id == user.id).scalar()),
        "cover_letters_generated": _as_int(
            db.query(func.count(CoverLetter.id)).filter(CoverLetter.user_id == user.id).scalar()),
        "applications_total": _as_int(app_total),
        "applications_submitted": _as_int(submitted),
        "applications_awaiting_action": _as_int(awaiting),
        "interviews": _as_int(interviews),
        "offers": _as_int(offers),
        "listings_updated_at": listings_updated_at,
        "profile_nudge": _profile_nudge(db, user),
    }


def _rate(n: int, d: int) -> float:
    return round(n / d * 100, 1) if d else 0.0


def admin_analytics(db: Session) -> dict:
    """Business-intelligence funnel + conversion rates (blueprint section 44)."""
    from collections import Counter
    from app.models.match import CandidateMatch

    total_matches = db.query(func.count(CandidateMatch.id)).scalar() or 0
    qualified = (db.query(func.count(CandidateMatch.id))
                 .filter(CandidateMatch.decision.in_(("APPLY", "REVIEW"))).scalar() or 0)
    rejected = (db.query(func.count(CandidateMatch.id))
                .filter(CandidateMatch.decision == "DO_NOT_APPLY").scalar() or 0)

    applications_total = db.query(func.count(Application.id)).scalar() or 0
    submitted = (db.query(func.count(Application.id))
                 .filter(Application.submitted_at.isnot(None)).scalar() or 0)
    interviews = (db.query(func.count(Application.id))
                  .filter(Application.status == "INTERVIEW").scalar() or 0)
    offers = (db.query(func.count(Application.id))
              .filter(Application.status == "OFFER").scalar() or 0)

    # Top companies by number of candidate matches.
    top_rows = (db.query(Company.company_name, func.count(CandidateMatch.id).label("n"))
                .join(Vacancy, Vacancy.company_id == Company.id)
                .join(CandidateMatch, CandidateMatch.vacancy_id == Vacancy.id)
                .group_by(Company.company_name)
                .order_by(func.count(CandidateMatch.id).desc()).limit(5).all())
    top_companies = [{"company": name, "matches": n} for name, n in top_rows]

    # Most common rejection reasons (first gap of DO_NOT_APPLY matches).
    rejected_matches = (db.query(CandidateMatch.gaps)
                        .filter(CandidateMatch.decision == "DO_NOT_APPLY").limit(2000).all())
    counter: Counter = Counter()
    for (gaps,) in rejected_matches:
        if gaps:
            counter[gaps[0]] += 1
    common_rejections = [{"reason": r, "count": c} for r, c in counter.most_common(5)]

    subs = {status: count for status, count in
            db.query(Subscription.status, func.count(Subscription.id)).group_by(Subscription.status).all()}

    return {
        "funnel": {
            "matches": total_matches, "qualified": qualified, "rejected": rejected,
            "applications": applications_total, "submitted": submitted,
            "interviews": interviews, "offers": offers,
        },
        "rates": {
            "qualified_rate": _rate(qualified, total_matches),
            "submit_rate": _rate(submitted, qualified),
            "interview_rate": _rate(interviews, submitted),
            "offer_rate": _rate(offers, submitted),
        },
        "top_companies_by_matches": top_companies,
        "common_rejection_reasons": common_rejections,
        "subscriptions_by_status": subs,
    }


def admin_dashboard(db: Session) -> dict:
    candidates = db.query(func.count(User.id)).filter(User.role == "candidate").scalar() or 0
    active_subs = (db.query(func.count(Subscription.id))
                   .filter(Subscription.status.in_(("ACTIVE", "TRIAL"))).scalar() or 0)
    paying_subs = (db.query(func.count(Subscription.id))
                   .filter(Subscription.status == "ACTIVE").scalar() or 0)

    def by_status_counts():
        rows = (db.query(Application.status, func.count(Application.id))
                .group_by(Application.status).all())
        return {status: count for status, count in rows}

    return {
        "registered_candidates": candidates,
        "active_subscriptions": active_subs,
        "paying_subscriptions": paying_subs,
        "estimated_mrr_zar": paying_subs * settings.PLAN_AMOUNT_ZAR,
        "companies_total": db.query(func.count(Company.id)).filter(Company.deleted_at.is_(None)).scalar() or 0,
        "companies_active": db.query(func.count(Company.id)).filter(Company.active.is_(True)).scalar() or 0,
        "sources_failing": (db.query(func.count(VacancySource.id))
                            .filter(VacancySource.consecutive_failures > 0).scalar() or 0),
        "vacancies_open": db.query(func.count(Vacancy.id)).filter(Vacancy.is_open.is_(True)).scalar() or 0,
        "vacancies_total": db.query(func.count(Vacancy.id)).scalar() or 0,
        "applications_total": db.query(func.count(Application.id)).scalar() or 0,
        "applications_by_status": by_status_counts(),
        "cv_versions_total": db.query(func.count(CVVersion.id)).scalar() or 0,
    }
