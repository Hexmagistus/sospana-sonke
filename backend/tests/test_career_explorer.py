"""Tests for the Career Explorer (qualification -> adjacent career families)."""
from datetime import datetime, timezone

from tests.conftest import register_and_login
from app.models.company import Company
from app.models.vacancy import Vacancy
from app.services.career_taxonomy import find_career_families


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_find_career_families_matches_keyword():
    fams = find_career_families("National Diploma in Biotechnology")
    assert fams and fams[0].label == "Biotechnology / Microbiology"
    assert "Laboratory Technician" in fams[0].related_careers


def test_find_career_families_no_match_returns_empty():
    assert find_career_families("Underwater basket weaving") == []
    assert find_career_families("") == []
    assert find_career_families(None) == []


def test_explorer_uses_explicit_qualification_param(client, db_engine):
    _, tokens = register_and_login(client)
    r = client.get("/api/v1/career-explorer", params={"qualification": "Biotechnology"},
                   headers=_auth(tokens))
    assert r.status_code == 200
    body = r.json()
    assert body["based_on"] == "Biotechnology"
    assert any(f["label"] == "Biotechnology / Microbiology" for f in body["families"])
    # Every related career carries a real (possibly zero) count, never omitted.
    for fam in body["families"]:
        for opt in fam["related_careers"]:
            assert isinstance(opt["open_vacancies"], int) and opt["open_vacancies"] >= 0


def test_explorer_falls_back_to_registration_answer(client, db_engine):
    email, password = "waterperson@example.com", "Password123!"
    reg = client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "first_name": "Sipho", "last_name": "Dlamini",
        "mobile_number": "0821234567", "qualification_name": "Diploma in Water Treatment",
    })
    assert reg.status_code == 201, reg.text
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    r = client.get("/api/v1/career-explorer", headers=_auth(tokens))
    assert r.status_code == 200
    body = r.json()
    assert body["based_on"] == "Diploma in Water Treatment"
    assert any(f["label"] == "Water & Wastewater Treatment" for f in body["families"])


def test_explorer_honest_when_nothing_to_go_on(client, db_engine):
    _, tokens = register_and_login(client)
    r = client.get("/api/v1/career-explorer", headers=_auth(tokens))
    assert r.status_code == 200
    body = r.json()
    assert body["based_on"] is None
    assert body["families"] == []


def test_explorer_counts_real_open_vacancies(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    c = Company(company_name="Lab Co", careers_url="https://boards.greenhouse.io/labco")
    s.add(c); s.commit(); s.refresh(c)
    now = datetime.now(timezone.utc)
    s.add(Vacancy(company_id=c.id, source_id="s1", title="Laboratory Technician",
                  content_hash="labh1", is_open=True, first_seen_at=now, last_seen_at=now))
    s.commit(); s.close()

    _, tokens = register_and_login(client)
    r = client.get("/api/v1/career-explorer", params={"qualification": "Biotechnology"},
                   headers=_auth(tokens))
    body = r.json()
    fam = next(f for f in body["families"] if f["label"] == "Biotechnology / Microbiology")
    lab_opt = next(o for o in fam["related_careers"] if o["title"] == "Laboratory Technician")
    assert lab_opt["open_vacancies"] == 1
