"""Document generation orchestration (blueprint Step 7).

Gathers the candidate's real profile data, builds a tailored CV / cover letter,
validates truthfulness, scores ATS compatibility, renders PDF + DOCX, stores them,
and persists a record. Truthfulness validation runs on every document.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.documents.builder import build_tailored_cv, safe_filename
from app.documents.cover_letter import build_cover_letter
from app.documents.ats import score_ats
from app.documents.render import render_cv_pdf, render_cv_docx, render_letter_pdf, render_letter_docx
from app.documents.truthfulness import ProfileFacts, validate_cv
from app.models.document import CVVersion, CoverLetter
from app.models.user import User
from app.matching.engine import VacancyData
from app.services.profile_service import get_full_profile_facts
from app.services.storage import get_storage


def _facts_and_truth(db: Session, user: User) -> tuple[dict, ProfileFacts]:
    """Kept as a thin wrapper — the assembly now lives in profile_service.py
    (get_full_profile_facts) so job_analysis_service.py and the Master CV
    endpoint use exactly the same "single source of truth" logic."""
    return get_full_profile_facts(db, user)


# ---- Ad-hoc tailoring: generate against ANY job the candidate provides ------
# (Works with no scraped vacancy — the candidate pastes/points at a role.)

def generate_cv_for_target(db: Session, user: User, job_title: str | None,
                           company_name: str | None, job_text: str | None,
                           template: str | None = None) -> CVVersion:
    facts, truth = _facts_and_truth(db, user)
    title = (job_title or "the role").strip() or "the role"
    skill_terms = VacancyData(title=title, description=job_text or "").skill_terms
    cv_data = build_tailored_cv(facts, {"title": title, "skill_terms": skill_terms})
    truth_result = validate_cv(cv_data, truth)
    ats, breakdown = score_ats(cv_data, skill_terms)
    template = template or "classic"

    label = safe_filename(facts["full_name"], title, company_name or "") + "_CV"
    version = CVVersion(
        user_id=user.id, match_id=None, vacancy_id=None, label=label, template=template,
        content=cv_data, ats_score=ats, ats_breakdown=breakdown,
        truthfulness_ok=truth_result.ok, truthfulness_violations=truth_result.violations or None,
        generated_by="deterministic",
    )
    db.add(version)
    db.flush()
    storage = get_storage()
    pdf_key = f"cv_versions/{user.id}/{version.id}.pdf"
    docx_key = f"cv_versions/{user.id}/{version.id}.docx"
    storage.put(pdf_key, render_cv_pdf(cv_data, template=template))
    storage.put(docx_key, render_cv_docx(cv_data, template=template))
    version.storage_key_pdf = pdf_key
    version.storage_key_docx = docx_key
    db.commit()
    db.refresh(version)
    return version


def build_cv_data_for_job(db: Session, user: User, title: str, skill_terms: set[str]) -> tuple[dict, object]:
    """Build (but do not persist or render) a tailored CV data structure and
    its truthfulness result for a given title/skill-term set. Used by the
    Fact-Check step (job_analysis_service.analyze_job / draft preview) so the
    candidate can review before anything is generated or saved."""
    facts, truth = _facts_and_truth(db, user)
    cv_data = build_tailored_cv(facts, {"title": title, "skill_terms": skill_terms})
    truth_result = validate_cv(cv_data, truth)
    return cv_data, truth_result


def persist_cv_version(db: Session, user: User, cv_data: dict, title: str, company_name: str | None,
                       skill_terms: set[str], template: str | None = None,
                       job_analysis_id: str | None = None) -> CVVersion:
    """Persist + render a CV version from an already-built (and possibly
    candidate-edited, post fact-check) cv_data structure. Re-validates
    truthfulness on the FINAL content, so an edit made after the fact-check
    step is still checked before anything is saved."""
    _, truth = _facts_and_truth(db, user)
    truth_result = validate_cv(cv_data, truth)
    ats, breakdown = score_ats(cv_data, skill_terms)
    template = template or "classic"

    label = safe_filename(cv_data.get("full_name", ""), title, company_name or "") + "_CV"
    version = CVVersion(
        user_id=user.id, match_id=None, vacancy_id=None, label=label, template=template,
        content=cv_data, ats_score=ats, ats_breakdown=breakdown,
        truthfulness_ok=truth_result.ok, truthfulness_violations=truth_result.violations or None,
        generated_by="deterministic",
    )
    db.add(version)
    db.flush()
    storage = get_storage()
    pdf_key = f"cv_versions/{user.id}/{version.id}.pdf"
    docx_key = f"cv_versions/{user.id}/{version.id}.docx"
    storage.put(pdf_key, render_cv_pdf(cv_data, template=template))
    storage.put(docx_key, render_cv_docx(cv_data, template=template))
    version.storage_key_pdf = pdf_key
    version.storage_key_docx = docx_key
    db.commit()
    db.refresh(version)
    return version


def generate_cover_letter_for_target(db: Session, user: User, job_title: str | None,
                                     company_name: str | None, job_text: str | None) -> CoverLetter:
    facts, truth = _facts_and_truth(db, user)
    title = (job_title or "the role").strip() or "the role"
    text = build_cover_letter(facts, company_name or None, title)
    truth_result = validate_cv({"summary": text, "skills": []}, truth)

    label = safe_filename(facts["full_name"], title, company_name or "") + "_CoverLetter"
    letter = CoverLetter(user_id=user.id, match_id=None, vacancy_id=None, label=label,
                         body=text, truthfulness_ok=truth_result.ok, generated_by="deterministic")
    db.add(letter)
    db.flush()
    storage = get_storage()
    pdf_key = f"cover_letters/{user.id}/{letter.id}.pdf"
    docx_key = f"cover_letters/{user.id}/{letter.id}.docx"
    storage.put(pdf_key, render_letter_pdf(text))
    storage.put(docx_key, render_letter_docx(text))
    letter.storage_key_pdf = pdf_key
    letter.storage_key_docx = docx_key
    db.commit()
    db.refresh(letter)
    return letter
