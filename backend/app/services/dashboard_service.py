"""Dashboard aggregation (blueprint sections 19, 21 & 44).

Read-only aggregate queries for the candidate dashboard and the admin/business
dashboard. All figures are computed deterministically from the database.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application
from app.models.company import Company
from app.models.document import CVVersion, CoverLetter
from app.models.match import CandidateMatch
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource
from app.services.subscription_service import get_or_create_subscription, has_active_access

_STRONG_BANDS = ("Strong", "Good")
_AWAITING = ("AWAITING_APPROVAL", "CANDIDATE_ACTION_REQUIRED")


def candidate_dashboard(db: Session, user: User) -> dict:
    sub = get_or_create_subscription(db, user.id)

    def match_count(**filt):
        q = db.query(func.count(CandidateMatch.id)).filter(CandidateMatch.user_id == user.id)
        for k, v in filt.items():
            q = q.filter(getattr(CandidateMatch, k) == v)
        return q.scalar() or 0

    def app_count(*statuses):
        q = db.query(func.count(Application.id)).filter(Application.user_id == user.id)
        if statuses:
            q = q.filter(Application.status.in_(statuses))
        return q.scalar() or 0

    strong = (db.query(func.count(CandidateMatch.id))
              .filter(CandidateMatch.user_id == user.id, CandidateMatch.band.in_(_STRONG_BANDS))
              .scalar() or 0)

    return {
        "subscription_status": sub.status,
        "has_access": has_active_access(sub),
        "plan_amount_zar": sub.amount_zar,
        "vacancies_open": db.query(func.count(Vacancy.id)).filter(Vacancy.is_open.is_(True)).scalar() or 0,
        "total_matches": match_count(),
        "strong_matches": strong,
        "apply_matches": match_count(decision="APPLY"),
        "cvs_generated": db.query(func.count(CVVersion.id)).filter(CVVersion.user_id == user.id).scalar() or 0,
        "cover_letters_generated": db.query(func.count(CoverLetter.id)).filter(CoverLetter.user_id == user.id).scalar() or 0,
        "applications_total": app_count(),
        "applications_submitted": app_count("SUBMITTED"),
        "applications_awaiting_action": app_count(*_AWAITING),
        "interviews": app_count("INTERVIEW"),
        "offers": app_count("OFFER"),
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
