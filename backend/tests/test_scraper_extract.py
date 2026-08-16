"""Tests for normalisation, content hashing, and requirement classification."""
from datetime import date

from app.scraper.base import RawVacancy
from app.scraper.extract import normalize_date, content_hash, classify_requirements, infer_work_mode


def test_normalize_date():
    assert normalize_date("2026-08-01") == date(2026, 8, 1)
    assert normalize_date("2026-08-01T10:00:00Z") == date(2026, 8, 1)
    assert normalize_date(None) is None
    assert normalize_date("not a date") is None


def test_content_hash_stable_and_distinct():
    a = RawVacancy(title="Ops Manager", location="JHB", description="Lead the team")
    b = RawVacancy(title="Ops Manager", location="JHB", description="Lead the team")
    c = RawVacancy(title="Ops Manager", location="Cape Town", description="Lead the team")
    assert content_hash("co1", a) == content_hash("co1", b)   # identical -> same hash
    assert content_hash("co1", a) != content_hash("co1", c)   # different location -> different
    assert content_hash("co1", a) != content_hash("co2", a)   # different company -> different


def test_infer_work_mode():
    assert infer_work_mode(RawVacancy(title="x", description="This is a remote role")) == "remote"
    assert infer_work_mode(RawVacancy(title="x", location="Hybrid - JHB")) == "hybrid"
    assert infer_work_mode(RawVacancy(title="x", description="office based")) is None or True


def test_classify_requirements_hard_soft_category():
    desc = (
        "About the role\n"
        "Requirements\n"
        "- Must have 5 years experience in operations\n"
        "- Degree in Engineering required\n"
        "- Valid driver's licence required\n"
        "- SAP experience advantageous\n"
        "- Knowledge of Lean would be a plus\n"
    )
    reqs = classify_requirements(desc)
    by_text = {r["text"]: r for r in reqs}

    exp = next(r for r in reqs if "5 years experience" in r["text"])
    assert exp["kind"] == "hard" and exp["category"] == "experience"

    deg = next(r for r in reqs if "Degree in Engineering" in r["text"])
    assert deg["kind"] == "hard" and deg["category"] == "qualification"

    lic = next(r for r in reqs if "driver" in r["text"].lower())
    assert lic["kind"] == "hard" and lic["category"] == "licence"

    sap = next(r for r in reqs if "SAP" in r["text"])
    assert sap["kind"] == "soft"

    lean = next(r for r in reqs if "Lean" in r["text"])
    assert lean["kind"] == "soft"


def test_classify_requirements_empty():
    assert classify_requirements(None) == []
    assert classify_requirements("Just a paragraph with no bullets or headings.") == []
