"""Engine inputs for the Job-Aligned CV builder (pasted job adverts) only.

Job matching against scraped vacancies has been removed: nothing here runs the
pre-filter, scores vacancies, writes ``candidate_matches`` rows or sends match
notifications any more. What remains builds the candidate's and a job's data
for the one-off analysis of a job the candidate pastes (job_analysis_service) and
for tailoring a CV to it.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.vocab import EDUCATION_RANK
from app.matching.config import MatchConfig
from app.matching.engine import CandidateData, VacancyData
from app.models.match import SystemSetting
from app.models.user import User
from app.models.profile import CandidateProfile, Education, Certification, Skill
from app.models.vacancy import Vacancy, VacancyRequirement

MATCH_CONFIG_KEY = "match_config"


def get_match_config(db: Session) -> MatchConfig:
    row = db.query(SystemSetting).filter(SystemSetting.key == MATCH_CONFIG_KEY).first()
    return MatchConfig.from_dict(row.value if row else None)


def _levels_in_text(text: str | None) -> set[str]:
    if not text:
        return set()
    blob = text.lower()
    return {kw for kw in EDUCATION_RANK if kw in blob}


def _education_levels(edu_rows: list[Education]) -> set[str]:
    levels: set[str] = set()
    for e in edu_rows:
        levels |= _levels_in_text(" ".join(x for x in [e.level, e.qualification] if x))
    return levels


def build_candidate_data(db: Session, user_id: str) -> tuple[CandidateData, CandidateProfile | None]:
    """Assemble the matching engine's input for a candidate.

    A full `CandidateProfile` is the primary source, but a candidate is
    matched against live vacancies even before they ever open the Profile
    page (e.g. the scheduled `match_all_candidates` job runs for everyone).
    So the free-text "Preferred post" / "Name of qualification" answers
    captured at registration (`User.preferred_position` /
    `User.qualification_name`) are folded in as extra signals -- added
    alongside whatever the profile already has (never replacing it), and
    still contributing even when no profile row exists at all yet.
    """
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    user = db.get(User, user_id)

    desired = list(profile.desired_occupations or []) if profile else []
    if user and user.preferred_position and user.preferred_position not in desired:
        desired.append(user.preferred_position)

    edu_levels = _education_levels(
        db.query(Education).filter(Education.profile_id == profile.id).all()
    ) if profile else set()
    if user:
        edu_levels |= _levels_in_text(user.qualification_name)

    if profile is None:
        return CandidateData(desired_occupations=desired, education_levels=edu_levels), None

    skills = {s.name.strip().lower() for s in
              db.query(Skill).filter(Skill.profile_id == profile.id).all()}
    certs = {c.name.strip().lower() for c in
             db.query(Certification).filter(Certification.profile_id == profile.id).all()}
    cand = CandidateData(
        years_experience=profile.years_experience,
        skills=skills,
        education_levels=edu_levels,
        certifications=certs,
        desired_occupations=desired,
        current_occupation=profile.current_occupation,
        industries={i.strip().lower() for i in (profile.industries or [])},
        preferred_locations=[p.strip().lower() for p in (profile.preferred_locations or [])],
        work_mode_preference=profile.work_mode_preference,
        willing_to_relocate=profile.willing_to_relocate,
        minimum_salary=profile.minimum_salary,
        has_drivers_licence=bool(profile.drivers_licence),
    )
    return cand, profile


def _salary_amount(vac: Vacancy) -> int | None:
    if not vac.salary:
        return None
    digits = "".join(ch for ch in vac.salary if ch.isdigit())
    return int(digits) if digits else None


def build_vacancy_data(db: Session, vac: Vacancy, sector: str | None) -> VacancyData:
    reqs = [{"text": r.text, "kind": r.kind, "category": r.category}
            for r in db.query(VacancyRequirement).filter(VacancyRequirement.vacancy_id == vac.id).all()]
    return VacancyData(title=vac.title, location=vac.location, work_mode=vac.work_mode,
                       salary_amount=_salary_amount(vac), description=vac.description,
                       company_sector=sector, requirements=reqs)
