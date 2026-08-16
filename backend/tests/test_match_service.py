"""Service-level tests for match orchestration and config persistence."""
from datetime import datetime, timezone

from app.models.user import User
from app.models.company import Company
from app.models.profile import CandidateProfile, Education, Skill
from app.models.vacancy import Vacancy, VacancyRequirement
from app.models.match import CandidateMatch
from app.core import security
from app.matching.config import MatchConfig
from app.services.match_service import (
    run_match_for_user, get_match_config, set_match_config, build_candidate_data,
)


def _make_candidate(db):
    user = User(email="thandi@x.co", password_hash=security.hash_password("Password123!"),
                first_name="Thandi", last_name="M", role="candidate", email_verified=True)
    db.add(user); db.commit(); db.refresh(user)
    profile = CandidateProfile(user_id=user.id, years_experience=6,
                               desired_occupations=["Operations Manager"], industries=["logistics"],
                               preferred_locations=["Johannesburg"])
    db.add(profile); db.commit(); db.refresh(profile)
    db.add(Education(profile_id=profile.id, institution="Wits", qualification="BCom", level="Degree"))
    db.add(Skill(profile_id=profile.id, name="SQL", category="technical"))
    db.add(Skill(profile_id=profile.id, name="Excel", category="software"))
    db.commit()
    return user


def _make_vacancy(db, title="Operations Manager", exp="5", location="Johannesburg", sector="Logistics"):
    company = Company(company_name="Acme", sector=sector, careers_url="https://boards.greenhouse.io/acme")
    db.add(company); db.commit(); db.refresh(company)
    now = datetime.now(timezone.utc)
    vac = Vacancy(company_id=company.id, source_id="s1", title=title, location=location,
                  description="Lead operations. SQL and Excel needed.", content_hash="h-" + title,
                  is_open=True, first_seen_at=now, last_seen_at=now)
    db.add(vac); db.commit(); db.refresh(vac)
    db.add(VacancyRequirement(vacancy_id=vac.id, text=f"Minimum of {exp} years experience required",
                              kind="hard", category="experience"))
    db.add(VacancyRequirement(vacancy_id=vac.id, text="Bachelor's degree required",
                              kind="hard", category="qualification"))
    db.commit()
    return company, vac


def test_build_candidate_data(db):
    user = _make_candidate(db)
    cand, profile = build_candidate_data(db, user.id)
    assert cand.years_experience == 6
    assert "sql" in cand.skills and "excel" in cand.skills
    assert "degree" in cand.education_levels
    assert cand.desired_occupations == ["Operations Manager"]


def test_run_match_creates_and_updates(db):
    user = _make_candidate(db)
    _make_vacancy(db)
    summary = run_match_for_user(db, user.id)
    assert summary.considered == 1
    assert summary.matched == 1 and summary.created == 1

    m = db.query(CandidateMatch).filter(CandidateMatch.user_id == user.id).one()
    assert m.decision == "APPLY" and m.hard_ok is True and m.status == "MATCHED"

    # Re-run: updates in place, no duplicate.
    summary2 = run_match_for_user(db, user.id)
    assert summary2.updated == 1 and summary2.created == 0
    assert db.query(CandidateMatch).filter(CandidateMatch.user_id == user.id).count() == 1


def test_run_match_rejects_when_underqualified(db):
    user = _make_candidate(db)
    _make_vacancy(db, title="Senior Ops Manager", exp="10")  # needs 10 years, candidate has 6
    run_match_for_user(db, user.id)
    m = db.query(CandidateMatch).filter(CandidateMatch.user_id == user.id).one()
    assert m.decision == "DO_NOT_APPLY" and m.status == "REJECTED" and m.hard_ok is False


def test_prefilter_excludes_role(db):
    user = _make_candidate(db)
    _make_vacancy(db, title="Cleaner")
    summary = run_match_for_user(db, user.id, excluded_roles={"cleaner"})
    assert summary.prefiltered_out == 1
    assert db.query(CandidateMatch).filter(CandidateMatch.user_id == user.id).count() == 0


def test_match_config_persistence(db):
    assert get_match_config(db).apply_threshold == 80.0
    cfg = MatchConfig(apply_threshold=70.0, review_threshold=50.0)
    set_match_config(db, cfg)
    assert get_match_config(db).apply_threshold == 70.0
