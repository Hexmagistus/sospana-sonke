"""Unit tests for the deterministic matching engine (no DB, no network)."""
from app.matching.config import MatchConfig
from app.matching.engine import (
    CandidateData, VacancyData, match, requirement_met, _required_years,
)


def _strong_candidate():
    return CandidateData(
        years_experience=6,
        skills={"sql", "excel", "operations management"},
        education_levels={"degree"},
        desired_occupations=["Operations Manager"],
        industries={"logistics"},
        preferred_locations=["johannesburg"],
        has_drivers_licence=True,
    )


def _ops_vacancy(exp_years=5, degree=True):
    reqs = [{"text": f"Minimum of {exp_years} years experience required", "kind": "hard", "category": "experience"}]
    if degree:
        reqs.append({"text": "Bachelor's degree required", "kind": "hard", "category": "qualification"})
    reqs.append({"text": "SAP experience advantageous", "kind": "soft", "category": "skill"})
    return VacancyData(
        title="Operations Manager", location="Johannesburg", company_sector="Logistics",
        description="Lead operations. Strong SQL and Excel skills needed.",
        requirements=reqs,
    )


def test_required_years_parsing():
    assert _required_years("Minimum of 5 years experience") == 5
    assert _required_years("8+ years") == 8
    assert _required_years("no number here") is None


def test_requirement_met_variants():
    cand = _strong_candidate()
    assert requirement_met(cand, {"text": "5 years experience", "kind": "hard", "category": "experience"}) is True
    assert requirement_met(cand, {"text": "10 years experience", "kind": "hard", "category": "experience"}) is False
    assert requirement_met(cand, {"text": "Bachelor's degree", "kind": "hard", "category": "qualification"}) is True
    assert requirement_met(cand, {"text": "Valid driver's licence", "kind": "hard", "category": "licence"}) is True
    assert requirement_met(cand, {"text": "Knowledge of SQL", "kind": "hard", "category": "skill"}) is True


def test_strong_match_applies():
    result = match(_strong_candidate(), _ops_vacancy())
    assert result.hard_ok is True
    assert result.score >= 80
    assert result.decision == "APPLY"
    assert result.band in ("Strong", "Good")
    assert result.confidence == "High"
    assert any("experience" in r.lower() for r in result.reasons)


def test_insufficient_experience_is_hard_reject():
    result = match(_strong_candidate(), _ops_vacancy(exp_years=8))
    assert result.hard_ok is False
    assert result.decision == "DO_NOT_APPLY"
    assert any("Mandatory requirement not satisfied" in g for g in result.gaps)


def test_missing_qualification_is_hard_reject():
    cand = _strong_candidate()
    cand.education_levels = set()  # no qualifications at all
    result = match(cand, _ops_vacancy())
    assert result.hard_ok is False
    assert result.decision == "DO_NOT_APPLY"
    assert any("degree" in g.lower() for g in result.gaps)


def test_weights_are_configurable():
    cand = _strong_candidate()
    cand.preferred_locations = ["cape town"]  # vacancy is in JHB, not remote -> low location score
    cand.willing_to_relocate = False
    vac = _ops_vacancy()
    default = match(cand, vac)
    # Make location dominate the weighting; score should drop noticeably.
    heavy_loc = MatchConfig(weights={"qualification": 1, "experience": 1, "skills": 1, "title": 1,
                                     "industry": 1, "location": 90, "certification": 1, "other": 1})
    weighted = match(cand, vac, heavy_loc)
    assert weighted.score < default.score


def test_band_thresholds():
    cfg = MatchConfig()
    assert cfg.band_for(90) == "Strong"
    assert cfg.band_for(78) == "Good"
    assert cfg.band_for(66) == "Possible"
    assert cfg.band_for(56) == "Weak"
    assert cfg.band_for(40) == "Reject"


def test_low_data_candidate_low_confidence():
    thin = CandidateData()  # empty profile
    result = match(thin, _ops_vacancy())
    assert result.confidence == "Low"
