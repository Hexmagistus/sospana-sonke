"""Orchestrates the "Tailor my CV to a job" pipeline (blueprint: AI CV
Enhancement & Job-Aligned CV Builder), for a job the candidate pastes in
directly rather than one scraped from a company's careers page.

Pipeline (mirrors the scraped-vacancy matching pipeline in match_service.py /
document_service.py, reusing the same deterministic engine rather than a
parallel one):

    pasted job text
      -> app.jobintel.parser.analyze_description   (requirement extraction)
      -> app.matching.engine.match                 (CV/job match report)
      -> app.documents.builder.build_tailored_cv    (draft CV, not saved)
      -> app.documents.truthfulness.validate_cv     (fact-check)
      -> app.documents.ats.score_ats                (ATS score)
      -> app.documents.quality.score_cv_quality     (CV quality score)
      -> readiness score/label/next-action
      -> persisted as one JobAnalysis row (blueprint: job analysis + match
         report + application-tracker row, all in one place)

Nothing here ever writes to the candidate's CandidateProfile ("Master CV") —
only app/services/profile_service.py's get_full_profile_facts is read from,
so tailoring a CV to a job can never alter the source of truth it was built
from.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.documents.ats import score_ats
from app.documents.cover_letter import build_cover_letter
from app.documents.quality import score_cv_quality
from app.documents.render import render_letter_pdf, render_letter_docx
from app.documents.builder import safe_filename
from app.documents.truthfulness import validate_cv
from app.jobintel.parser import analyze_description
from app.matching.engine import VacancyData, match, requirement_met
from app.models.document import CoverLetter
from app.models.job_analysis import JobAnalysis, JOB_APPLICATION_STATUSES
from app.models.user import User
from app.services.document_service import build_cv_data_for_job, persist_cv_version
from app.services.match_service import build_candidate_data, get_match_config
from app.services.profile_service import get_full_profile_facts
from app.services.storage import get_storage


# ---- scoring helpers not covered by the scraped-vacancy engine --------------

def _score_industry(facts: dict, jd_industries: list[str]) -> float:
    """The scraped-vacancy engine scores industry fit against a company's
    admin-set sector, which a pasted advert doesn't have. Score instead by
    overlap between the candidate's stated industries and the industries the
    advert itself names — still deterministic, still nothing invented."""
    if not jd_industries:
        return 70.0  # advert names no specific industry — neutral, not a gap
    cand_industries = {i.strip().lower() for i in (facts.get("industries") or [])}
    if not cand_industries:
        return 50.0  # unknown either way — neutral-low, not a claim of absence
    return 100.0 if (cand_industries & {i.lower() for i in jd_industries}) else 45.0


def _score_responsibility(facts: dict, requirements: list[dict]) -> float:
    """Token-overlap between the candidate's own responsibilities/achievements
    text and the advert's duty bullets — a real, computed comparison of the
    candidate's own words against the advert's, never a guess."""
    resp_texts = [r["text"] for r in requirements if r.get("category") == "responsibility"]
    if not resp_texts:
        return 70.0
    cv_blob = " ".join(
        f"{e.get('responsibilities') or ''} {e.get('achievements') or ''}"
        for e in (facts.get("experience") or [])
    ).lower()
    cv_tokens = {t for t in re.findall(r"[a-z]+", cv_blob) if len(t) > 3}
    if not cv_tokens:
        return 30.0
    ratios = []
    for text in resp_texts:
        req_tokens = {t for t in re.findall(r"[a-z]+", text.lower()) if len(t) > 3}
        if req_tokens:
            ratios.append(len(cv_tokens & req_tokens) / len(req_tokens))
    return round(sum(ratios) / len(ratios) * 100, 1) if ratios else 70.0


def _classify_requirements(cand, requirements: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Strong Matches / Partial Matches / Missing Requirements. A missing item
    is ALWAYS phrased "not found in your CV" — never "you don't have this" —
    because absence from the CV is not proof the candidate lacks the thing."""
    strong, partial, missing = [], [], []
    for req in requirements:
        outcome = requirement_met(cand, req)
        if outcome is True:
            strong.append({"text": req["text"],
                           "note": f"Found in your CV — matches this {req['category']} requirement."})
        elif outcome is False:
            if req.get("kind") == "hard":
                missing.append({"text": req["text"],
                                "note": "Not found in your CV. This is listed as a mandatory "
                                        "requirement, so it's worth addressing before you apply."})
            else:
                partial.append({"text": req["text"],
                                "note": "Not found in your CV. This is a preferred (not mandatory) "
                                        "requirement — a gap, but not disqualifying."})
        else:
            partial.append({"text": req["text"],
                            "note": "Could not be automatically verified from your CV — please "
                                    "check this one against your own experience."})
    return strong, partial, missing


def _readiness(match_score: float, ats_score: float, quality_score: float) -> tuple[float, str, str]:
    overall = round(0.5 * match_score + 0.3 * ats_score + 0.2 * quality_score, 1)
    if overall >= 80:
        return overall, "Ready to apply", ("Your CV is in strong shape for this role. Review the "
                                           "final preview, export it, and apply.")
    if overall >= 65:
        return overall, "Almost ready", ("Address the flagged gaps and quality suggestions below, "
                                         "then re-check the readiness score before applying.")
    if overall >= 45:
        return overall, "Needs work", ("Several gaps and quality issues need attention before this "
                                       "CV is ready to send for this role.")
    return overall, "Not ready yet", ("This role may not be a strong match yet — review the missing "
                                      "requirements below, or consider a role closer to your current "
                                      "experience.")


# ---- main pipeline ------------------------------------------------------------

def analyze_job(db: Session, user: User, job_title: str | None, company_name: str | None,
                job_description: str) -> tuple[JobAnalysis, dict, list[str]]:
    """Runs the full pipeline and PERSISTS the JobAnalysis row (the Job
    Analysis record, Match Report and Application-tracker row are the same
    row). Returns (job_analysis, draft_cv_data, fact_check_violations) — the
    draft CV is not itself persisted so the candidate can review/edit it
    (the Fact-Check step) before choosing to generate the final documents via
    generate_cv() below."""
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Paste the job advertisement text to analyse it.")

    parsed = analyze_description(job_description, job_title)
    cand, _ = build_candidate_data(db, user.id)
    vdata = VacancyData(title=parsed.title, description=job_description, requirements=parsed.requirements)
    config = get_match_config(db)
    result = match(cand, vdata, config)
    skill_terms = vdata.skill_terms

    facts, _ = get_full_profile_facts(db, user)
    cv_data, truth_result = build_cv_data_for_job(db, user, parsed.title, skill_terms)
    ats_score, ats_breakdown = score_ats(cv_data, skill_terms)
    quality = score_cv_quality(cv_data, skill_terms, match_score=result.score)

    sub_scores = {
        "qualification": result.sub_scores["qualification"],
        "experience": result.sub_scores["experience"],
        "technical_skill": result.sub_scores["skills"],
        "industry": _score_industry(facts, parsed.industries),
        "certification": result.sub_scores["certification"],
        "keyword": ats_breakdown["keyword_relevance"],
        "responsibility": _score_responsibility(facts, parsed.requirements),
    }
    strong, partial, missing = _classify_requirements(cand, parsed.requirements)
    readiness_score, readiness_label, action = _readiness(result.score, ats_score, quality["overall"])

    analysis = JobAnalysis(
        user_id=user.id, job_title=parsed.title, company_name=(company_name or "").strip() or None,
        job_description=job_description, extracted=parsed.to_dict(),
        match_score=result.score, sub_scores=sub_scores, band=result.band, decision=result.decision,
        confidence=result.confidence, hard_ok=result.hard_ok,
        strong_matches=strong, partial_matches=partial, missing_requirements=missing,
        ats_score=ats_score, ats_breakdown=ats_breakdown,
        quality_score=quality["overall"], quality_breakdown=quality["breakdown"],
        quality_suggestions=quality["suggestions"],
        readiness_score=readiness_score, readiness_label=readiness_label, recommended_action=action,
        template="professional", status="PREPARING",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis, cv_data, truth_result.violations


def _owned(db: Session, user: User, job_analysis_id: str) -> JobAnalysis:
    row = db.get(JobAnalysis, job_analysis_id)
    if row is None or row.user_id != user.id or row.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")
    return row


def generate_cv(db: Session, user: User, job_analysis_id: str, cv_data: dict, template: str | None = None):
    """Persist + render the final CV — the candidate's (possibly edited,
    post fact-check) draft, in the chosen template. Truthfulness is
    re-validated on this exact final content before saving."""
    analysis = _owned(db, user, job_analysis_id)
    skill_terms = VacancyData(
        title=analysis.job_title, description=analysis.job_description,
        requirements=analysis.extracted.get("requirements") or [],
    ).skill_terms
    template = template or analysis.template or "professional"
    version = persist_cv_version(db, user, cv_data, analysis.job_title, analysis.company_name,
                                 skill_terms, template=template)
    analysis.cv_version_id = version.id
    analysis.template = template
    db.commit()
    return version


def generate_cover_letter(db: Session, user: User, job_analysis_id: str):
    analysis = _owned(db, user, job_analysis_id)
    facts, truth = get_full_profile_facts(db, user)
    text = build_cover_letter(facts, analysis.company_name, analysis.job_title)
    truth_result = validate_cv({"summary": text, "skills": []}, truth)

    label = safe_filename(facts["full_name"], analysis.job_title, analysis.company_name or "") + "_CoverLetter"
    letter = CoverLetter(user_id=user.id, match_id=None, vacancy_id=None, label=label, body=text,
                         truthfulness_ok=truth_result.ok, generated_by="deterministic")
    db.add(letter)
    db.flush()
    storage = get_storage()
    pdf_key = f"cover_letters/{user.id}/{letter.id}.pdf"
    docx_key = f"cover_letters/{user.id}/{letter.id}.docx"
    storage.put(pdf_key, render_letter_pdf(text))
    storage.put(docx_key, render_letter_docx(text))
    letter.storage_key_pdf = pdf_key
    letter.storage_key_docx = docx_key
    analysis.cover_letter_id = letter.id
    db.commit()
    db.refresh(letter)
    return letter


# ---- application tracker CRUD ------------------------------------------------

def list_job_analyses(db: Session, user: User) -> list[JobAnalysis]:
    return (db.query(JobAnalysis)
            .filter(JobAnalysis.user_id == user.id, JobAnalysis.deleted_at.is_(None))
            .order_by(JobAnalysis.created_at.desc()).all())


def get_job_analysis(db: Session, user: User, job_analysis_id: str) -> JobAnalysis:
    return _owned(db, user, job_analysis_id)


def update_tracker(db: Session, user: User, job_analysis_id: str, status_value: str | None,
                   notes: str | None, date_applied: date | None) -> JobAnalysis:
    analysis = _owned(db, user, job_analysis_id)
    if status_value is not None:
        status_value = status_value.upper()
        if status_value not in JOB_APPLICATION_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Status must be one of {', '.join(JOB_APPLICATION_STATUSES)}.")
        analysis.status = status_value
        if status_value == "APPLIED" and analysis.date_applied is None and date_applied is None:
            analysis.date_applied = date.today()
    if notes is not None:
        analysis.notes = notes
    if date_applied is not None:
        analysis.date_applied = date_applied
    db.commit()
    db.refresh(analysis)
    return analysis


def delete_job_analysis(db: Session, user: User, job_analysis_id: str) -> None:
    analysis = _owned(db, user, job_analysis_id)
    analysis.deleted_at = datetime.now(timezone.utc)
    db.commit()
