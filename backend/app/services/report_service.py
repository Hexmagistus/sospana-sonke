"""Candidate report generation (blueprint section 18)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.documents.builder import safe_filename
from app.documents.report_render import render_report_pdf
from app.models.application import Application
from app.models.company import Company
from app.models.document import CVVersion, CoverLetter
from app.models.match import CandidateMatch
from app.models.report import Report
from app.models.user import User
from app.models.vacancy import Vacancy
from app.services.storage import get_storage


def build_report_stats(db: Session, user: User) -> dict:
    matches = db.query(CandidateMatch).filter(CandidateMatch.user_id == user.id).all()
    qualified = [m for m in matches if m.decision in ("APPLY", "REVIEW")]
    rejected = [m for m in matches if m.decision == "DO_NOT_APPLY"]

    def title_company(m):
        vac = db.get(Vacancy, m.vacancy_id)
        company = db.get(Company, vac.company_id) if vac else None
        return (vac.title if vac else "—"), (company.company_name if company else "—")

    top = sorted(qualified, key=lambda m: m.score, reverse=True)[:5]
    top_out = []
    for m in top:
        title, company = title_company(m)
        top_out.append({"title": title, "company": company, "score": m.score, "status": m.status})

    rej_out = []
    for m in rejected[:5]:
        title, company = title_company(m)
        reason = (m.gaps[0] if m.gaps else "No specific reason recorded.")
        rej_out.append({"title": title, "company": company, "reason": reason})

    def app_count(*statuses):
        q = db.query(func.count(Application.id)).filter(Application.user_id == user.id)
        if statuses:
            q = q.filter(Application.status.in_(statuses))
        return q.scalar() or 0

    return {
        "candidate_name": f"{user.first_name} {user.last_name}".strip(),
        "date": datetime.now(timezone.utc).strftime("%d %B %Y"),
        "vacancies_analyzed": len(matches),
        "qualified": len(qualified),
        "rejected": len(rejected),
        "cvs_generated": db.query(func.count(CVVersion.id)).filter(CVVersion.user_id == user.id).scalar() or 0,
        "cover_letters_generated": db.query(func.count(CoverLetter.id)).filter(CoverLetter.user_id == user.id).scalar() or 0,
        "applications_submitted": app_count("SUBMITTED", "INTERVIEW", "OFFER"),
        "requiring_action": app_count("CANDIDATE_ACTION_REQUIRED", "AWAITING_APPROVAL"),
        "top_applications": top_out,
        "rejected_examples": rej_out,
    }


def generate_candidate_report(db: Session, user: User) -> Report:
    stats = build_report_stats(db, user)
    label = safe_filename(stats["candidate_name"], "Report", stats["date"].replace(" ", "_"))
    report = Report(user_id=user.id, label=label, stats=stats)
    db.add(report)
    db.flush()
    key = f"reports/{user.id}/{report.id}.pdf"
    get_storage().put(key, render_report_pdf(stats))
    report.storage_key_pdf = key
    db.commit()
    from app.services.notification_service import notify_report_ready
    notify_report_ready(db, user=user, report=report)
    db.commit()
    db.refresh(report)
    return report
