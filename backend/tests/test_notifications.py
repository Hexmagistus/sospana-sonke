"""Tests for notifications and the admin scheduler."""
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
                    description="SQL needed.", application_url="https://apply.example.com/1",
                    content_hash="h-" + title, is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        s.add(VacancyRequirement(vacancy_id=v.id, text="Minimum of 5 years experience required",
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
        "preferred_locations": ["Johannesburg"]})
    client.post("/api/v1/profile/skills", headers=h, json={"name": "SQL", "category": "technical"})


def test_strong_match_notification(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    client.post("/api/v1/matches/run", headers=_auth(tokens))

    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert any(n["type"] == "strong_match" for n in notes)
    assert client.get("/api/v1/notifications/unread-count", headers=_auth(tokens)).json()["unread"] >= 1


def test_notification_idempotent_across_reruns(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    client.post("/api/v1/matches/run", headers=_auth(tokens))
    client.post("/api/v1/matches/run", headers=_auth(tokens))  # rerun
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "strong_match"]
    assert len(notes) == 1  # not duplicated


def test_mark_read_flow(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    client.post("/api/v1/matches/run", headers=_auth(tokens))
    note = client.get("/api/v1/notifications", headers=_auth(tokens)).json()[0]
    assert client.post(f"/api/v1/notifications/{note['id']}/read", headers=_auth(tokens)).json()["is_read"] is True
    client.post("/api/v1/notifications/read-all", headers=_auth(tokens))
    assert client.get("/api/v1/notifications/unread-count", headers=_auth(tokens)).json()["unread"] == 0


def test_action_required_notification(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "assisted", "auto_apply_enabled": False, "min_match_score": 0,
        "max_applications_per_day": 5, "max_applications_per_week": 25,
        "excluded_companies": [], "excluded_roles": []})
    client.post("/api/v1/matches/run", headers=_auth(tokens))
    match_id = client.get("/api/v1/matches", headers=_auth(tokens)).json()[0]["id"]
    client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens))
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert any(n["type"] == "action_required" for n in notes)


def test_report_ready_notification(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    client.post("/api/v1/matches/run", headers=_auth(tokens))
    client.post("/api/v1/reports/generate", headers=_auth(tokens))
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert any(n["type"] == "report_ready" for n in notes)


# ---- scheduler (admin) ----

def _admin(client, db_engine):
    email, password = make_admin(db_engine)
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()


def test_schedule_defaults_and_update(client, db_engine):
    admin = _admin(client, db_engine)
    got = client.get("/api/v1/admin/schedule", headers=_auth(admin)).json()["schedule"]
    assert "scan_all_companies" in got and "match_all_candidates" in got

    upd = client.put("/api/v1/admin/schedule", headers=_auth(admin),
                     json={"schedule": {"scan_all_companies": "0 */12 * * *"}}).json()["schedule"]
    assert upd["scan_all_companies"] == "0 */12 * * *"


def test_schedule_requires_admin(client):
    _, tokens = register_and_login(client)
    assert client.get("/api/v1/admin/schedule", headers=_auth(tokens)).status_code == 403


def test_trigger_job_and_run_log(client, db_engine):
    admin = _admin(client, db_engine)
    run = client.post("/api/v1/admin/jobs/match_all_candidates/run", headers=_auth(admin))
    assert run.status_code == 200 and run.json()["status"] == "success"
    runs = client.get("/api/v1/admin/jobs/runs", headers=_auth(admin)).json()
    assert any(r["job_name"] == "match_all_candidates" for r in runs)


def test_trigger_unknown_job(client, db_engine):
    admin = _admin(client, db_engine)
    assert client.post("/api/v1/admin/jobs/nope/run", headers=_auth(admin)).status_code == 404
