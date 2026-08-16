"""Profile helpers: get-or-create, and applying a parsed CV to the profile."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.profile import CandidateProfile, Education, Certification, WorkExperience, Skill


def get_or_create_profile(db: Session, user_id: str) -> CandidateProfile:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    if profile is None:
        profile = CandidateProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


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
