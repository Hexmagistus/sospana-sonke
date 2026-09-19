"""Daily Agent orchestration (proactive, always-human-approved job-search agent).

Turns the Career Agent from "search when you visit" into "working for you in
the background": on a schedule (see app/scheduler/jobs.py:run_daily_agent), it
refreshes each candidate's matches, then for the strongest ones that don't yet
have an application, auto-drafts a tailored CV + cover letter and prepares a
ready-to-review Application.

Hard constraint: this module NEVER submits anything to an employer and NEVER
calls anything in app.automation. Every application it prepares lands in
AWAITING_APPROVAL (approval mode, the default) or CANDIDATE_ACTION_REQUIRED
(automatic/assisted mode) — both states that already require the candidate to
act (approve, then open the link and submit, or click "Try automated
submission" themselves). It only reuses the existing, already-safe
prepare_application() pipeline; it adds no new submission path.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationSettings
from app.models.match import CandidateMatch
from app.models.user import User
from app.services.application_service import get_or_create_settings, prepare_application
from app.services.document_service import generate_cover_letter_for_match, generate_cv_for_match
from app.services.match_service import run_match_for_user
from app.services.notification_service import notify_daily_agent_briefing

logger = logging.getLogger(__name__)


@dataclass
class AgentRunSummary:
    new_matches: int = 0
    cvs_generated: int = 0
    cover_letters_generated: int = 0
    applications_prepared: int = 0
    applications_ready: list = field(default_factory=list)  # Application ids
    skipped: int = 0


def _candidate_unactioned_matches(db: Session, user_id: str, settings: ApplicationSettings,
                                  limit: int) -> list[CandidateMatch]:
    """The candidate's best matches that don't have an application yet and pass
    their own gates (decision, minimum score) — best score first."""
    already_applied_vacancy_ids = {
        row[0] for row in
        db.query(Application.vacancy_id).filter(Application.user_id == user_id).all()
    }
    q = (db.query(CandidateMatch)
         .filter(CandidateMatch.user_id == user_id,
                 CandidateMatch.decision != "DO_NOT_APPLY",
                 CandidateMatch.score >= settings.min_match_score)
         .order_by(CandidateMatch.score.desc())
         .limit(max(limit * 10, 50)))  # over-fetch since some will already be applied-to

    out: list[CandidateMatch] = []
    for m in q.all():
        if m.vacancy_id in already_applied_vacancy_ids:
            continue
        out.append(m)
        if len(out) >= limit:
            break
    return out


def run_daily_agent_for_user(db: Session, user: User, max_new: int = 3,
                             run_matching: bool = True, job_run_id: str | None = None) -> AgentRunSummary:
    """The per-candidate daily pipeline. Refreshes matches (unless disabled),
    then for up to `max_new` of the strongest matches with no application yet,
    generates a tailored CV + cover letter and prepares the application. Stops
    early (without raising) if the candidate's own daily/weekly application
    caps are reached mid-batch — whatever was prepared before that still
    stands, and the rest wait for tomorrow's run.
    """
    summary = AgentRunSummary()
    settings = get_or_create_settings(db, user.id)

    if run_matching:
        excluded_companies = {c.strip().lower() for c in (settings.excluded_companies or []) if c}
        excluded_roles = {r.strip().lower() for r in (settings.excluded_roles or []) if r}
        match_summary = run_match_for_user(db, user.id, excluded_companies=excluded_companies,
                                           excluded_roles=excluded_roles)
        summary.new_matches = match_summary.created

    candidates = _candidate_unactioned_matches(db, user.id, settings, limit=max_new)
    for m in candidates:
        try:
            generate_cv_for_match(db, user, m.id)
            summary.cvs_generated += 1
            generate_cover_letter_for_match(db, user, m.id)
            summary.cover_letters_generated += 1
            app = prepare_application(db, user, m.id)
            summary.applications_prepared += 1
            summary.applications_ready.append(app.id)
        except HTTPException as exc:
            summary.skipped += 1
            if exc.status_code == http_status.HTTP_429_TOO_MANY_REQUESTS:
                # Daily/weekly cap reached -- no point trying the rest today.
                break
            continue
        except Exception:
            logger.warning("Daily agent: failed to process match %s for user %s",
                           m.id, user.id, exc_info=True)
            summary.skipped += 1
            continue

    if summary.applications_ready:
        notify_daily_agent_briefing(db, user=user, application_ids=summary.applications_ready,
                                    job_run_id=job_run_id)
        db.commit()

    return summary


def run_daily_agent(db: Session, job_run_id: str | None = None, max_new_per_user: int = 3) -> dict:
    """Run the Daily Agent for every active candidate. This is the function
    wired into the scheduler registry (and reachable via
    POST /cron/run/run_daily_agent) so "daily" actually happens on its own.
    """
    users = db.query(User).filter(User.role == "candidate", User.is_active.is_(True)).all()
    totals = AgentRunSummary()
    candidates_with_new_apps = 0
    for user in users:
        try:
            s = run_daily_agent_for_user(db, user, max_new=max_new_per_user, job_run_id=job_run_id)
        except Exception:
            logger.warning("Daily agent: run failed for user %s", user.id, exc_info=True)
            db.rollback()
            continue
        totals.new_matches += s.new_matches
        totals.cvs_generated += s.cvs_generated
        totals.cover_letters_generated += s.cover_letters_generated
        totals.applications_prepared += s.applications_prepared
        totals.skipped += s.skipped
        if s.applications_ready:
            candidates_with_new_apps += 1

    return {
        "candidates_processed": len(users),
        "candidates_with_new_applications": candidates_with_new_apps,
        "new_matches": totals.new_matches,
        "cvs_generated": totals.cvs_generated,
        "cover_letters_generated": totals.cover_letters_generated,
        "applications_prepared": totals.applications_prepared,
        "skipped": totals.skipped,
    }
