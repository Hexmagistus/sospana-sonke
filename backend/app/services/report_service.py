"""Candidate report generation (blueprint section 18)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.documents.builder import safe_filename
from app.documents.report_render import render_report_pdf
from app.models.application import Application
from app.models.document import CVVersion, CoverLetter
from app.models.report import Report
from app.models.user import User
from app.services.storage import get_storage


def build_report_stats(db: Session, user: User) -> dict:
    def app_count(*statuses):
        q = db.query(func.count(Application.id)).filter(Application.user_id == user.id)
        if statuses:
            q = q.filter(Application.status.in_(statuses))
        return q.scalar() or 0

    return {
        "candidate_name": f"{user.first_name} {user.last_name}".strip(),
        "date": datetime.now(timezone.utc).strftime("%d %B %Y"),
        "cvs_generated": db.query(func.count(CVVersion.id)).filter(CVVersion.user_id == user.id).scalar() or 0,
        "cover_letters_generated": db.query(func.count(CoverLetter.id)).filter(CoverLetter.user_id == user.id).scalar() or 0,
        "applications_submitted": app_count("SUBMITTED", "INTERVIEW", "OFFER"),
        "requiring_action": app_count("CANDIDATE_ACTION_REQUIRED", "AWAITING_APPROVAL"),
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
