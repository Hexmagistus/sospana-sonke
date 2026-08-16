"""Automation orchestration (blueprint sections 13, 14, 28).

Given a prepared application, decide whether automated submission is permitted and
possible; if so, fill truthfully and submit; otherwise fall back to a clear
action-required package. Every outcome is recorded on the application's audit trail.
Safety order: global switch → per-source policy → live blocker detection → unknowns.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.automation.base import Submitter
from app.automation.detector import classify_page, extract_form_fields
from app.automation.planner import build_answer_map, plan_submission
from app.core.config import settings
from app.models.application import Application
from app.models.company import Company
from app.models.user import User
from app.models.vacancy import Vacancy
from app.services.application_service import _log, _transition
from app.services.document_service import _facts_and_truth


def _action_required(db: Session, app: Application, note: str, detail: str) -> Application:
    app.action_required_note = note
    _transition(db, app, "CANDIDATE_ACTION_REQUIRED", "auto_submit_deferred",
                actor="system", detail=detail)
    db.commit()
    db.refresh(app)
    return app


def attempt_auto_submit(db: Session, user: User, app: Application,
                        submitter: Submitter | None = None) -> Application:
    vac = db.get(Vacancy, app.vacancy_id)
    company = db.get(Company, vac.company_id) if vac else None
    url = app.application_url or (vac.application_url if vac else None)

    # 1) Global kill-switch (automation is opt-in).
    if not settings.AUTOMATION_ENABLED:
        return _action_required(db, app, "Automated submission is not enabled on this platform. "
                                "Please submit on the employer site and mark as submitted.",
                                "Global automation disabled.")

    # 2) Per-source policy.
    mode = (company.automation_mode if company else "assisted")
    if mode in ("manual", "disabled"):
        return _action_required(db, app, "This employer is set to manual applications. "
                                "Please submit on their site and mark as submitted.",
                                f"Source policy = {mode}.")
    if not url:
        _transition(db, app, "APPLICATION_FAILED", "auto_submit_failed", actor="system",
                    detail="No application URL available.")
        db.commit(); db.refresh(app)
        return app

    # 3) Load the page and detect blockers (never bypassed).
    if submitter is None:
        from app.automation.playwright_submitter import PlaywrightSubmitter
        submitter = PlaywrightSubmitter()
    try:
        html = submitter.load(url)
    except Exception as exc:
        _transition(db, app, "APPLICATION_FAILED", "auto_submit_failed", actor="system",
                    detail=f"Could not load application page: {type(exc).__name__}: {exc}")
        db.commit(); db.refresh(app)
        return app

    blockers = classify_page(html, requires_login_hint=bool(company and company.requires_login),
                             has_captcha_hint=bool(company and company.has_captcha))
    if blockers.blocking:
        return _action_required(db, app, " ".join(blockers.reasons()),
                                "Blockers detected: " + "; ".join(blockers.reasons()))

    # 4) Plan a truthful fill; unknown required fields force candidate input.
    facts, _ = _facts_and_truth(db, user)
    plan = plan_submission(extract_form_fields(html), build_answer_map(facts))
    if plan.unknown_required:
        return _action_required(
            db, app, "Some required fields need your input: " + ", ".join(plan.unknown_required),
            "Unknown required fields: " + ", ".join(plan.unknown_required))

    # 5) Assisted mode prepares but does not auto-submit; only 'auto' submits.
    if mode != "auto":
        return _action_required(db, app, "Your application is prepared and pre-filled. "
                                "Please review and submit on the employer site.",
                                "Assisted mode — candidate completes submission.")

    result = submitter.fill_and_submit(url, plan.values)
    if result.status == "submitted":
        app.submitted_at = datetime.now(timezone.utc)
        app.submission_method = "auto"
        _log(db, app, "auto_submitted", actor="system",
             detail=f"Auto-submitted {len(plan.values)} fields.")
        _transition(db, app, "SUBMITTED", "auto_submitted", actor="system",
                    detail="Automated submission succeeded.")
    else:
        _transition(db, app, "APPLICATION_FAILED", "auto_submit_failed", actor="system",
                    detail=result.reason or "Submission failed.")
    db.commit()
    db.refresh(app)
    return app
