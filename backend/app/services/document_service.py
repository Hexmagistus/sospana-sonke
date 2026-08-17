"""Document generation orchestration (blueprint Step 7).

Gathers the candidate's real profile data, builds a tailored CV / cover letter,
validates truthfulness, scores ATS compatibility, renders PDF + DOCX, stores them,
and persists a record. Truthfulness validation runs on every document.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.documents.builder import build_tailored_cv, safe_filename
from app.documents.cover_letter import build_cover_letter
from app.documents.ats import score_ats
from app.documents.render import render_cv_pdf, render_cv_docx, render_letter_pdf, render_letter_docx
from app.documents.truthfulness import ProfileFacts, validate_cv
from app.models.company import Company
from app.models.document import CVVersion, CoverLetter
from app.models.match import CandidateMatch
from app.models.profile import CandidateProfile, Education, Certification, Skill, WorkExperience
from app.models.user import User
from app.models.vacancy import Vacancy
from app.matching.engine import VacancyData
from app.services.match_service import build_vacancy_data
from app.services.storage import get_storage


def _facts_and_truth(db: Session, user: User) -> tuple[dict, ProfileFacts]:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    skills = db.query(Skill).filter(Skill.profile_id == profile.id).all() if profile else []
    edu = db.query(Education).filter(Education.profile_id == profile.id).all() if profile else []
    certs = db.query(Certification).filter(Certification.profile_id == profile.id).all() if profile else []
    work = db.query(WorkExperience).filter(WorkExperience.profile_id == profile.id).all() if profile else []

    facts = {
        "full_name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "phone": user.mobile_number,
        "city": profile.city if profile else None,
        "country": profile.country if profile else None,
        "linkedin_url": profile.linkedin_url if profile else None,
        "github_url": profile.github_url if profile else None,
        "portfolio_url": profile.portfolio_url if profile else None,
        "current_occupation": profile.current_occupation if profile else None,
        "desired_occupations": (profile.desired_occupations or []) if profile else [],
        "industries": (profile.industries or []) if profile else [],
        "years_experience": profile.years_experience if profile else None,
        "drivers_licence": profile.drivers_licence if profile else None,
        "work_authorization": profile.work_authorization if profile else None,
        "minimum_salary": profile.minimum_salary if profile else None,
        "willing_to_relocate": profile.willing_to_relocate if profile else None,
        "languages": (profile.languages or []) if profile else [],
        "skills": [s.name for s in skills],
        "education": [{"institution": e.institution, "qualification": e.qualification,
                       "field_of_study": e.field_of_study, "level": e.level,
                       "completion_date": e.completion_date.isoformat() if e.completion_date else None}
                      for e in edu],
        "certifications": [{"name": c.name, "issuing_organization": c.issuing_organization} for c in certs],
        "experience": [{"employer": w.employer, "position": w.position,
                        "start_date": w.start_date.isoformat() if w.start_date else None,
                        "end_date": w.end_date.isoformat() if w.end_date else None,
                        "is_current": w.is_current, "responsibilities": w.responsibilities,
                        "achievements": w.achievements} for w in work],
    }
    truth = ProfileFacts(
        skills={s.name.strip().lower() for s in skills},
        employers={w.employer.strip().lower() for w in work if w.employer},
        institutions={e.institution.strip().lower() for e in edu if e.institution},
        certifications={c.name.strip().lower() for c in certs if c.name},
        years_experience=profile.years_experience if profile else None,
    )
    return facts, truth


def _match_context(db: Session, user: User, match_id: str) -> tuple[CandidateMatch, Vacancy, Company]:
    match = db.get(CandidateMatch, match_id)
    if match is None or match.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    vac = db.get(Vacancy, match.vacancy_id)
    if vac is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found.")
    company = db.get(Company, vac.company_id)
    return match, vac, company


def generate_cv_for_match(db: Session, user: User, match_id: str) -> CVVersion:
    match, vac, company = _match_context(db, user, match_id)
    facts, truth = _facts_and_truth(db, user)

    vdata = build_vacancy_data(db, vac, company.sector if company else None)
    skill_terms = vdata.skill_terms
    cv_data = build_tailored_cv(facts, {"title": vac.title, "skill_terms": skill_terms})

    truth_result = validate_cv(cv_data, truth)
    ats, breakdown = score_ats(cv_data, skill_terms)

    label = safe_filename(facts["full_name"], vac.title, company.company_name if company else "") + "_CV"
    version = CVVersion(
        user_id=user.id, match_id=match.id, vacancy_id=vac.id, label=label,
        content=cv_data, ats_score=ats, ats_breakdown=breakdown,
        truthfulness_ok=truth_result.ok, truthfulness_violations=truth_result.violations or None,
        generated_by="deterministic",
    )
    db.add(version)
    db.flush()

    storage = get_storage()
    pdf_key = f"cv_versions/{user.id}/{version.id}.pdf"
    docx_key = f"cv_versions/{user.id}/{version.id}.docx"
    storage.put(pdf_key, render_cv_pdf(cv_data))
    storage.put(docx_key, render_cv_docx(cv_data))
    version.storage_key_pdf = pdf_key
    version.storage_key_docx = docx_key

    # Update tracking status (blueprint section 17): a CV now exists for this match.
    if match.status in ("MATCHED",):
        match.status = "CV_CREATED"
    db.commit()
    db.refresh(version)
    return version


def generate_cover_letter_for_match(db: Session, user: User, match_id: str) -> CoverLetter:
    match, vac, company = _match_context(db, user, match_id)
    facts, truth = _facts_and_truth(db, user)

    text = build_cover_letter(facts, company.company_name if company else None, vac.title)
    # Truthfulness: validate the letter's factual claims (years) against the profile.
    truth_result = validate_cv({"summary": text, "skills": []}, truth)

    label = safe_filename(facts["full_name"], vac.title, company.company_name if company else "") + "_CoverLetter"
    letter = CoverLetter(user_id=user.id, match_id=match.id, vacancy_id=vac.id, label=label,
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


# ---- Ad-hoc tailoring: generate against ANY job the candidate provides ------
# (Works with no scraped vacancy — the candidate pastes/points at a role.)

def generate_cv_for_target(db: Session, user: User, job_title: str | None,
                           company_name: str | None, job_text: str | None) -> CVVersion:
    facts, truth = _facts_and_truth(db, user)
    title = (job_title or "the role").strip() or "the role"
    skill_terms = VacancyData(title=title, description=job_text or "").skill_terms
    cv_data = build_tailored_cv(facts, {"title": title, "skill_terms": skill_terms})
    truth_result = validate_cv(cv_data, truth)
    ats, breakdown = score_ats(cv_data, skill_terms)

    label = safe_filename(facts["full_name"], title, company_name or "") + "_CV"
    version = CVVersion(
        user_id=user.id, match_id=None, vacancy_id=None, label=label,
        content=cv_data, ats_score=ats, ats_breakdown=breakdown,
        truthfulness_ok=truth_result.ok, truthfulness_violations=truth_result.violations or None,
        generated_by="deterministic",
    )
    db.add(version)
    db.flush()
    storage = get_storage()
    pdf_key = f"cv_versions/{user.id}/{version.id}.pdf"
    docx_key = f"cv_versions/{user.id}/{version.id}.docx"
    storage.put(pdf_key, render_cv_pdf(cv_data))
    storage.put(docx_key, render_cv_docx(cv_data))
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
