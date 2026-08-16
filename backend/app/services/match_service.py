"""Match orchestration (blueprint sections 8-10 & 17).

Builds the deterministic inputs from the candidate's profile and each vacancy,
runs the pre-filter then the scoring engine, and upserts an explainable
CandidateMatch per vacancy. Idempotent: re-running updates existing matches.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.common.vocab import EDUCATION_RANK
from app.matching.config import MatchConfig
from app.matching.engine import CandidateData, VacancyData, match
from app.matching.prefilter import prefilter
from app.models.company import Company
from app.models.match import CandidateMatch, SystemSetting
from app.models.profile import CandidateProfile, Education, Certification, Skill
from app.models.vacancy import Vacancy, VacancyRequirement

MATCH_CONFIG_KEY = "match_config"


def get_match_config(db: Session) -> MatchConfig:
    row = db.query(SystemSetting).filter(SystemSetting.key == MATCH_CONFIG_KEY).first()
    return MatchConfig.from_dict(row.value if row else None)


def set_match_config(db: Session, config: MatchConfig) -> MatchConfig:
    row = db.query(SystemSetting).filter(SystemSetting.key == MATCH_CONFIG_KEY).first()
    if row is None:
        row = SystemSetting(key=MATCH_CONFIG_KEY, value=config.to_dict(),
                            description="Matching engine weights and thresholds.")
        db.add(row)
    else:
        row.value = config.to_dict()
        row.version += 1
    db.commit()
    return config


def _education_levels(edu_rows: list[Education]) -> set[str]:
    levels: set[str] = set()
    for e in edu_rows:
        blob = " ".join(x for x in [e.level, e.qualification] if x).lower()
        for kw in EDUCATION_RANK:
            if kw in blob:
                levels.add(kw)
    return levels


def build_candidate_data(db: Session, user_id: str) -> tuple[CandidateData, CandidateProfile | None]:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    if profile is None:
        return CandidateData(), None
    skills = {s.name.strip().lower() for s in
              db.query(Skill).filter(Skill.profile_id == profile.id).all()}
    edu_rows = db.query(Education).filter(Education.profile_id == profile.id).all()
    certs = {c.name.strip().lower() for c in
             db.query(Certification).filter(Certification.profile_id == profile.id).all()}
    cand = CandidateData(
        years_experience=profile.years_experience,
        skills=skills,
        education_levels=_education_levels(edu_rows),
        certifications=certs,
        desired_occupations=list(profile.desired_occupations or []),
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


@dataclass
class MatchRunSummary:
    considered: int = 0
    prefiltered_out: int = 0
    matched: int = 0        # decision APPLY or REVIEW
    rejected: int = 0       # decision DO_NOT_APPLY
    created: int = 0
    updated: int = 0
    match_ids: list[str] = field(default_factory=list)


def _upsert_match(db: Session, user_id: str, vac: Vacancy, result) -> tuple[CandidateMatch, bool]:
    existing = (db.query(CandidateMatch)
                .filter(CandidateMatch.user_id == user_id, CandidateMatch.vacancy_id == vac.id)
                .first())
    status = "REJECTED" if result.decision == "DO_NOT_APPLY" else "MATCHED"
    created = existing is None
    if existing is None:
        existing = CandidateMatch(user_id=user_id, vacancy_id=vac.id)
        db.add(existing)
    existing.score = result.score
    existing.sub_scores = result.sub_scores
    existing.band = result.band
    existing.decision = result.decision
    existing.confidence = result.confidence
    existing.hard_ok = result.hard_ok
    existing.reasons = result.reasons
    existing.gaps = result.gaps
    existing.status = status
    existing.engine_version = "deterministic-v1"
    return existing, created


def run_match_for_user(db: Session, user_id: str, vacancy_ids: list[str] | None = None,
                       excluded_companies: set[str] | None = None,
                       excluded_roles: set[str] | None = None,
                       limit: int = 500, notify: bool = True) -> MatchRunSummary:
    cand, _ = build_candidate_data(db, user_id)
    config = get_match_config(db)
    excluded_companies = excluded_companies or set()
    excluded_roles = excluded_roles or set()
    summary = MatchRunSummary()

    q = db.query(Vacancy).filter(Vacancy.is_open.is_(True), Vacancy.deleted_at.is_(None))
    if vacancy_ids:
        q = q.filter(Vacancy.id.in_(vacancy_ids))
    vacancies = q.limit(limit).all()

    # Cache company sector lookups.
    sector_cache: dict[str, tuple[str | None, str]] = {}
    fresh_strong: list = []  # (match, title, company) for newly-found strong matches

    for vac in vacancies:
        summary.considered += 1
        if vac.company_id not in sector_cache:
            company = db.get(Company, vac.company_id)
            sector_cache[vac.company_id] = (company.sector if company else None,
                                            company.company_name if company else "")
        sector, company_name = sector_cache[vac.company_id]

        pf = prefilter(vacancy_title=vac.title, company_name=company_name,
                       vacancy_salary=_salary_amount(vac),
                       excluded_companies=excluded_companies, excluded_roles=excluded_roles,
                       minimum_salary=cand.minimum_salary)
        if not pf.passes:
            summary.prefiltered_out += 1
            continue

        vdata = build_vacancy_data(db, vac, sector)
        result = match(cand, vdata, config)
        m, created = _upsert_match(db, user_id, vac, result)
        summary.created += int(created)
        summary.updated += int(not created)
        if result.decision == "DO_NOT_APPLY":
            summary.rejected += 1
        else:
            summary.matched += 1
        if created and (result.band in ("Strong", "Good") or result.decision == "APPLY"):
            fresh_strong.append((m, vac.title, company_name))

    db.commit()

    # Notify the candidate about newly-found strong matches (idempotent).
    if notify and fresh_strong:
        from app.models.user import User
        from app.services.notification_service import notify_strong_match
        user = db.get(User, user_id)
        if user:
            for m, title, cname in fresh_strong:
                notify_strong_match(db, user=user, match=m, vacancy_title=title, company_name=cname)
            db.commit()

    # Collect ids for the response.
    ids = [m.id for m in db.query(CandidateMatch).filter(CandidateMatch.user_id == user_id).all()]
    summary.match_ids = ids
    return summary
