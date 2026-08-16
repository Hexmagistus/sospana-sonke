"""Tests for candidate dashboard, admin dashboard, and report generation."""
from datetime import datetime, timezone

from tests.conftest import register_and_login, make_admin
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancyRequirement


def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def _seed_vacancy(db_engine, title="Operations Manager"):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine); s = S()
    try:
        c = Company(company_name="Acme Logistics", sector="Logistics",
                    careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title=title, location="Johannesburg",
                    description="SQL and Excel needed.", content_hash="h-" + title,
                    is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        s.add(VacancyRequirement(vacancy_id=v.id, text="Minimum of 5 years experience required",
                                 kind="hard", category="experience"))
        s.commit()
        return v.id
    finally:
        s.close()


def _prep(client, tokens, db_engine):
    h = _auth(tokens)
    client.put("/api/v1/profile", headers=h, json={
        "years_experience": 6, "current_occupation": "Operations Supervisor",
        "desired_occupations": ["Operations Manager"], "industries": ["logistics"],
        "preferred_locations": ["Johannesburg"]})
    client.post("/api/v1/profile/skills", headers=h, json={"name": "SQL", "category": "technical"})
    _seed_vacancy(db_engine)
    client.post("/api/v1/matches/run", headers=h)
    return client.get("/api/v1/matches", headers=h).json()[0]["id"]


def test_candidate_dashboard(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _prep(client, tokens, db_engine)
    client.post(f"/api/v1/matches/{match_id}/generate-cv", headers=_auth(tokens))
    client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))

    d = client.get("/api/v1/dashboard", headers=_auth(tokens))
    assert d.status_code == 200
    body = d.json()
    assert body["total_matches"] == 1
    assert body["vacancies_open"] == 1
    assert body["cvs_generated"] == 1
    assert body["applications_total"] == 1
    assert body["subscription_status"] == "TRIAL" and body["plan_amount_zar"] == 100


def test_admin_dashboard_requires_admin(client, db_engine):
    _, tokens = register_and_login(client)
    assert client.get("/api/v1/admin/dashboard", headers=_auth(tokens)).status_code == 403


def test_admin_dashboard_mrr(client, db_engine):
    # One candidate who pays -> ACTIVE -> counts toward MRR at R100.
    _, cand = register_and_login(client, email="payer@example.com")
    client.post("/api/v1/subscription/mock-pay", headers=_auth(cand))

    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    d = client.get("/api/v1/admin/dashboard", headers=_auth(admin))
    assert d.status_code == 200
    body = d.json()
    assert body["paying_subscriptions"] >= 1
    assert body["estimated_mrr_zar"] == body["paying_subscriptions"] * 100
    assert body["registered_candidates"] >= 1


def test_report_generate_and_download(client, db_engine):
    _, tokens = register_and_login(client)
    _prep(client, tokens, db_engine)

    gen = client.post("/api/v1/reports/generate", headers=_auth(tokens))
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["stats"]["vacancies_analyzed"] == 1
    assert "candidate_name" in body["stats"]

    dl = client.get(f"/api/v1/reports/{body['id']}/download", headers=_auth(tokens))
    assert dl.status_code == 200 and dl.content[:5] == b"%PDF-"

    listed = client.get("/api/v1/reports", headers=_auth(tokens)).json()
    assert len(listed) == 1


def test_report_ownership(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    _prep(client, tokens_a, db_engine)
    rep = client.post("/api/v1/reports/generate", headers=_auth(tokens_a)).json()
    assert client.get(f"/api/v1/reports/{rep['id']}", headers=_auth(tokens_b)).status_code == 404
    assert client.get(f"/api/v1/reports/{rep['id']}/download", headers=_auth(tokens_b)).status_code == 404
