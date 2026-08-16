"""Tests for application lifecycle, audit trail, answers, caps, and preferences."""
from datetime import datetime, timezone

from tests.conftest import register_and_login
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancyRequirement
from app.models.match import CandidateMatch


def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def _seed_vacancy(db_engine, title="Operations Manager", exp="5"):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        c = Company(company_name="Acme Logistics", sector="Logistics",
                    careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title=title, location="Johannesburg",
                    description="SQL and Excel needed.", application_url="https://apply.example.com/1",
                    content_hash="h-" + title, is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        s.add(VacancyRequirement(vacancy_id=v.id, text=f"Minimum of {exp} years experience required",
                                 kind="hard", category="experience"))
        s.commit()
        return v.id
    finally:
        s.close()


def _enrich(client, tokens):
    h = _auth(tokens)
    client.put("/api/v1/profile", headers=h, json={
        "years_experience": 6, "current_occupation": "Operations Supervisor",
        "desired_occupations": ["Operations Manager"], "industries": ["logistics"],
        "preferred_locations": ["Johannesburg"], "minimum_salary": 45000,
        "work_authorization": "South African citizen", "drivers_licence": "Code 08",
        "willing_to_relocate": True,
    })
    client.post("/api/v1/profile/skills", headers=h, json={"name": "SQL", "category": "technical"})


def _make_match(client, tokens, db_engine, title="Operations Manager", exp="5"):
    _enrich(client, tokens)
    _seed_vacancy(db_engine, title=title, exp=exp)
    client.post("/api/v1/matches/run", headers=_auth(tokens))
    return client.get("/api/v1/matches", headers=_auth(tokens)).json()[0]["id"]


def test_preferences_default_and_update(client):
    _, tokens = register_and_login(client)
    got = client.get("/api/v1/preferences", headers=_auth(tokens)).json()
    assert got["application_mode"] == "approval" and got["max_applications_per_day"] == 5

    upd = client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "assisted", "auto_apply_enabled": False, "min_match_score": 75,
        "max_applications_per_day": 3, "max_applications_per_week": 10,
        "excluded_companies": [], "excluded_roles": ["cleaner"]})
    assert upd.status_code == 200 and upd.json()["application_mode"] == "assisted"


def test_prepare_generates_answers_with_unknowns(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)
    r = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))
    assert r.status_code == 201, r.text
    app = r.json()
    assert app["status"] == "AWAITING_APPROVAL"  # default approval mode
    qs = {a["question"]: a for a in app["answers"]}
    # Factual answer we have -> known; notice period -> unknown; motivational -> ai_generated.
    assert not qs["How many years of relevant experience do you have?"]["is_unknown"]
    assert qs["What is your notice period?"]["is_unknown"] is True
    assert any(a["source"] == "ai_generated" for a in app["answers"])


def test_full_lifecycle_with_audit_trail(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)
    app = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens)).json()

    approved = client.post(f"/api/v1/applications/{app['id']}/approve", headers=_auth(tokens)).json()
    assert approved["status"] == "CANDIDATE_ACTION_REQUIRED" and approved["authorised_at"]

    submitted = client.post(f"/api/v1/applications/{app['id']}/mark-submitted", headers=_auth(tokens)).json()
    assert submitted["status"] == "SUBMITTED" and submitted["submitted_at"]

    interview = client.post(f"/api/v1/applications/{app['id']}/status", headers=_auth(tokens),
                            json={"status": "interview"}).json()
    assert interview["status"] == "INTERVIEW"

    detail = client.get(f"/api/v1/applications/{app['id']}", headers=_auth(tokens)).json()
    types = [e["event_type"] for e in detail["events"]]
    assert "prepared" in types and "approved" in types and "submitted" in types and "status_update" in types


def test_duplicate_application_blocked(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)
    first = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))
    assert first.status_code == 201
    dup = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))
    assert dup.status_code == 409


def test_min_score_gate(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)
    client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "approval", "auto_apply_enabled": False, "min_match_score": 99.5,
        "max_applications_per_day": 5, "max_applications_per_week": 25,
        "excluded_companies": [], "excluded_roles": []})
    r = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))
    assert r.status_code == 409 and "below your minimum" in r.json()["detail"]


def test_daily_cap_enforced(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)
    client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "approval", "auto_apply_enabled": False, "min_match_score": 0,
        "max_applications_per_day": 0, "max_applications_per_week": 25,
        "excluded_companies": [], "excluded_roles": []})
    r = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))
    assert r.status_code == 429


def test_do_not_apply_match_blocked(client, db_engine):
    _, tokens = register_and_login(client)
    me = client.get("/api/v1/auth/me", headers=_auth(tokens)).json()
    vac_id = _seed_vacancy(db_engine)
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine); s = S()
    try:
        m = CandidateMatch(user_id=me["id"], vacancy_id=vac_id, score=40.0, band="Reject",
                           decision="DO_NOT_APPLY", confidence="High", hard_ok=False, status="REJECTED")
        s.add(m); s.commit(); s.refresh(m)
        match_id = m.id
    finally:
        s.close()
    r = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))
    assert r.status_code == 409 and "DO NOT APPLY" in r.json()["detail"]


def test_fill_unknown_answer(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)
    app = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens)).json()
    notice = next(a for a in app["answers"] if a["question"] == "What is your notice period?")
    filled = client.put(f"/api/v1/applications/{app['id']}/answers/{notice['id']}",
                        headers=_auth(tokens), json={"value": "30 days"}).json()
    assert filled["answer"] == "30 days" and filled["source"] == "candidate" and filled["is_unknown"] is False


def test_invalid_status_rejected(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)
    app = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens)).json()
    r = client.post(f"/api/v1/applications/{app['id']}/status", headers=_auth(tokens),
                    json={"status": "SUBMITTED"})  # not a candidate-settable status
    assert r.status_code == 400


def test_application_ownership(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    match_id = _make_match(client, tokens_a, db_engine)
    app = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens_a)).json()
    assert client.get(f"/api/v1/applications/{app['id']}", headers=_auth(tokens_b)).status_code == 404
    assert client.get("/api/v1/applications", headers=_auth(tokens_b)).json() == []


def test_settings_exclusions_feed_matching(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine, title="Cleaner")
    client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "approval", "auto_apply_enabled": False, "min_match_score": 70,
        "max_applications_per_day": 5, "max_applications_per_week": 25,
        "excluded_companies": [], "excluded_roles": ["cleaner"]})
    run = client.post("/api/v1/matches/run", headers=_auth(tokens)).json()
    assert run["prefiltered_out"] == 1 and run["matched"] == 0
