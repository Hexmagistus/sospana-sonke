"""Route-level tests for matching and admin match-config."""
from datetime import datetime, timezone

from tests.conftest import register_and_login, make_admin
from app.models.company import Company
from app.models.profile import CandidateProfile, Skill, Education
from app.models.user import User
from app.models.vacancy import Vacancy, VacancyRequirement


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed_vacancy(db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        c = Company(company_name="Acme", sector="Logistics",
                    careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title="Operations Manager",
                    location="Johannesburg", description="SQL and Excel needed.",
                    content_hash="h1", is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        s.add(VacancyRequirement(vacancy_id=v.id, text="Minimum of 5 years experience required",
                                 kind="hard", category="experience"))
        s.commit()
        return v.id
    finally:
        s.close()


def _enrich_profile(client, tokens):
    h = _auth(tokens)
    client.put("/api/v1/profile", headers=h, json={
        "years_experience": 6, "desired_occupations": ["Operations Manager"],
        "industries": ["logistics"], "preferred_locations": ["Johannesburg"],
    })
    client.post("/api/v1/profile/skills", headers=h, json={"name": "SQL", "category": "technical"})
    client.post("/api/v1/profile/education", headers=h,
                json={"institution": "Wits", "qualification": "BCom", "level": "Degree"})


def test_run_and_list_matches(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich_profile(client, tokens)
    _seed_vacancy(db_engine)

    run = client.post("/api/v1/matches/run", headers=_auth(tokens))
    assert run.status_code == 200, run.text
    assert run.json()["considered"] == 1

    matches = client.get("/api/v1/matches", headers=_auth(tokens)).json()
    assert len(matches) == 1
    assert matches[0]["vacancy_title"] == "Operations Manager"
    assert matches[0]["decision"] in ("APPLY", "REVIEW")

    detail = client.get(f"/api/v1/matches/{matches[0]['id']}", headers=_auth(tokens)).json()
    assert "sub_scores" in detail and "reasons" in detail


def test_match_ownership(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    _enrich_profile(client, tokens_a)
    _seed_vacancy(db_engine)
    client.post("/api/v1/matches/run", headers=_auth(tokens_a))
    a_match = client.get("/api/v1/matches", headers=_auth(tokens_a)).json()[0]

    # B sees no matches and cannot open A's match.
    assert client.get("/api/v1/matches", headers=_auth(tokens_b)).json() == []
    assert client.get(f"/api/v1/matches/{a_match['id']}", headers=_auth(tokens_b)).status_code == 404


def test_match_config_admin_only(client, db_engine):
    _, tokens = register_and_login(client)
    assert client.get("/api/v1/admin/match-config", headers=_auth(tokens)).status_code == 403

    email, password = make_admin(db_engine)
    admin_tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    got = client.get("/api/v1/admin/match-config", headers=_auth(admin_tokens))
    assert got.status_code == 200 and got.json()["apply_threshold"] == 80.0

    upd = client.put("/api/v1/admin/match-config", headers=_auth(admin_tokens),
                     json={"weights": {"qualification": 30, "experience": 30, "skills": 20,
                                       "title": 10, "industry": 3, "location": 3,
                                       "certification": 2, "other": 2},
                           "apply_threshold": 75, "review_threshold": 55,
                           "bands": {"strong": 85, "good": 75, "possible": 65, "weak": 55}})
    assert upd.status_code == 200 and upd.json()["apply_threshold"] == 75
