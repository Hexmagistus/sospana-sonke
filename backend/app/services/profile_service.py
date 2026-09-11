"""Profile helpers: get-or-create, assembling the "Master CV" facts, and
applying a parsed CV to the profile."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.profile import CandidateProfile, Education, Certification, WorkExperience, Skill
from app.models.user import User


def get_or_create_profile(db: Session, user_id: str) -> CandidateProfile:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    if profile is None:
        profile = CandidateProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def get_full_profile_facts(db: Session, user: User):
    """Assemble the candidate's complete, verified career record — their
    "Master CV" — as a flat facts dict plus a ProfileFacts truthfulness set.

    This is the SINGLE source every generated CV/cover letter/interview prep
    is built from (app/services/document_service.py, job_analysis_service.py).
    It only ever reads CandidateProfile and its children; nothing here writes
    to the profile, so the Master CV is never altered by generating a
    tailored document.
    """
    from app.documents.truthfulness import ProfileFacts  # local import: avoids a cycle at module load

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
        "professional_memberships": (profile.professional_memberships or []) if profile else [],
        "skills": [s.name for s in skills],
        "skills_detailed": [{"name": s.name, "category": s.category,
                             "confirmed_by_candidate": s.confirmed_by_candidate} for s in skills],
        "education": [{"institution": e.institution, "qualification": e.qualification,
                       "field_of_study": e.field_of_study, "level": e.level,
                       "completion_date": e.completion_date.isoformat() if e.completion_date else None,
                       "confirmed_by_candidate": e.confirmed_by_candidate}
                      for e in edu],
        "certifications": [{"name": c.name, "issuing_organization": c.issuing_organization,
                            "confirmed_by_candidate": c.confirmed_by_candidate} for c in certs],
        "experience": [{"employer": w.employer, "position": w.position,
                        "start_date": w.start_date.isoformat() if w.start_date else None,
                        "end_date": w.end_date.isoformat() if w.end_date else None,
                        "is_current": w.is_current, "responsibilities": w.responsibilities,
                        "achievements": w.achievements, "technologies": w.technologies or [],
                        "industry": w.industry, "confirmed_by_candidate": w.confirmed_by_candidate}
                       for w in work],
    }
    truth = ProfileFacts(
        skills={s.name.strip().lower() for s in skills},
        employers={w.employer.strip().lower() for w in work if w.employer},
        institutions={e.institution.strip().lower() for e in edu if e.institution},
        certifications={c.name.strip().lower() for c in certs if c.name},
        years_experience=profile.years_experience if profile else None,
    )
    return facts, truth


def apply_structured_to_profile(
    db: Session, profile: CandidateProfile, structured: dict, opts: dict
) -> dict:
    """Import an AI suggestion as UNCONFIRMED child records (source='cv_extraction').

    Nothing here is marked confirmed — the candidate must verify each item. Existing
    confirmed data is never overwritten; we only add. Duplicate skills are skipped.
    """
    added = {"skills": 0, "education": 0, "work_experience": 0, "certifications": 0, "profile_fields": []}

    if opts.get("contact_and_links", True):
        for field in ("linkedin_url", "github_url", "portfolio_url"):
            val = structured.get(field)
            if val and getattr(profile, field) in (None, ""):
                setattr(profile, field, val)
                added["profile_fields"].append(field)
        langs = structured.get("languages")
        if langs and not profile.languages:
            profile.languages = langs
            added["profile_fields"].append("languages")

    if opts.get("skills", True) and structured.get("skills"):
        existing = {s.name.lower() for s in profile.skills}
        for item in structured["skills"]:
            name = (item.get("name") or "").strip()
            if name and name.lower() not in existing:
                existing.add(name.lower())
                db.add(Skill(profile_id=profile.id, name=name, category=item.get("category"),
                             confirmed_by_candidate=False, source="cv_extraction"))
                added["skills"] += 1

    if opts.get("education", True) and structured.get("education"):
        for item in structured["education"]:
            inst = (item.get("institution") or "").strip()
            if inst:
                db.add(Education(profile_id=profile.id, institution=inst[:200],
                                 qualification=item.get("qualification"),
                                 field_of_study=item.get("field_of_study"),
                                 level=item.get("level"),
                                 confirmed_by_candidate=False, source="cv_extraction"))
                added["education"] += 1

    if opts.get("work_experience", True) and structured.get("work_experience"):
        for item in structured["work_experience"]:
            emp = (item.get("employer") or "").strip()
            if emp:
                db.add(WorkExperience(profile_id=profile.id, employer=emp[:200],
                                      position=item.get("position"),
                                      responsibilities=item.get("responsibilities"),
                                      technologies=item.get("technologies") or [],
                                      confirmed_by_candidate=False, source="cv_extraction"))
                added["work_experience"] += 1

    if opts.get("certifications", True) and structured.get("certifications"):
        for item in structured["certifications"]:
            name = (item.get("name") or "").strip()
            if name:
                db.add(Certification(profile_id=profile.id, name=name[:200],
                                     issuing_organization=item.get("issuing_organization"),
                                     confirmed_by_candidate=False, source="cv_extraction"))
                added["certifications"] += 1

    db.commit()
    return added
