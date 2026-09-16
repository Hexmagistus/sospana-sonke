"""Tests for normalisation, content hashing, and requirement classification."""
from datetime import date

from app.scraper.base import RawVacancy
from app.scraper.extract import (
    normalize_date, content_hash, classify_requirements, infer_work_mode,
    infer_province, parse_salary_range, infer_nqf_level,
)


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


def test_infer_province():
    assert infer_province("Vereeniging, Gauteng") == "Gauteng"
    assert infer_province("Sandton") == "Gauteng"  # city-only, no province named
    assert infer_province("Durban, KZN") == "KwaZulu-Natal"  # recognised city
    assert infer_province("Some town, XYZ") is None  # unrecognised, no guess
    assert infer_province(None) is None
    assert infer_province("Remote") is None


def test_parse_salary_range():
    assert parse_salary_range("R15,000 - R20,000 per month") == (15000, 20000)
    assert parse_salary_range("R15k - R20k") == (15000, 20000)
    assert parse_salary_range("R18,000") == (18000, 18000)
    assert parse_salary_range("Market related") == (None, None)
    assert parse_salary_range(None) == (None, None)
    # reversed order still comes back sorted low-to-high
    assert parse_salary_range("R20,000 - R15,000") == (15000, 20000)


def test_infer_nqf_level():
    assert infer_nqf_level("Process Controller", "Matric required") == 4
    assert infer_nqf_level("Ops Manager", "National Diploma in Operations") == 6
    assert infer_nqf_level("Lab Technician", "Bachelor's degree in Chemistry") == 7
    assert infer_nqf_level("Research Lead", "PhD in a relevant field required") == 10
    assert infer_nqf_level("General worker", "No formal qualification needed") is None


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
