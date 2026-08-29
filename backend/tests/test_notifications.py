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


# ---- broad "new jobs" alert ----

def test_new_jobs_broadcast_notifies_active_candidates(client, db_engine):
    from app.services.notification_service import notify_new_jobs_broadcast
    from sqlalchemy.orm import sessionmaker

    _, tokens = register_and_login(client)
    vac_id = _seed_vacancy(db_engine, title="Warehouse Supervisor")

    S = sessionmaker(bind=db_engine)
    db = S()
    try:
        sent = notify_new_jobs_broadcast(db, vacancy_ids=[vac_id], job_run_id="run-1")
        db.commit()
    finally:
        db.close()

    assert sent == 1
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "new_jobs"]
    assert len(notes) == 1
    assert "Warehouse Supervisor" in notes[0]["body"]


def test_new_jobs_broadcast_idempotent_per_job_run(client, db_engine):
    from app.services.notification_service import notify_new_jobs_broadcast
    from sqlalchemy.orm import sessionmaker

    _, tokens = register_and_login(client)
    vac_id = _seed_vacancy(db_engine, title="Store Clerk")

    S = sessionmaker(bind=db_engine)
    db = S()
    try:
        notify_new_jobs_broadcast(db, vacancy_ids=[vac_id], job_run_id="run-2")
        db.commit()
        sent_again = notify_new_jobs_broadcast(db, vacancy_ids=[vac_id], job_run_id="run-2")
        db.commit()
    finally:
        db.close()

    assert sent_again == 0  # same job_run_id -> idempotent, no duplicate
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "new_jobs"]
    assert len(notes) == 1


def test_scan_due_companies_alerts_on_new_vacancies(client, db_engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company
    from app.scheduler.runner import run_job

    _, tokens = register_and_login(client)

    # Seed the "newly discovered" vacancy up front (its own committed transaction) so
    # the fake scan below only has to report its id — mirrors how scan_source really
    # works (create the row, then hand the id to the alerting step). Doing the write
    # here rather than inside the monkeypatched scan avoids two sessions holding open
    # writes against the same SQLite file at once ("database is locked").
    vac_id = _seed_vacancy(db_engine, title="Retail Assistant")

    S = sessionmaker(bind=db_engine)
    db = S()
    try:
        db.add(Company(company_name="Fresh Foods Ltd", careers_url="https://boards.greenhouse.io/freshfoods",
                       active=True))
        db.commit()
    finally:
        db.close()

    from app.services import scan_service as scan_service_module

    def _fake_scan_company(db, company, client=None, check_robots=True):
        report = scan_service_module.ScanReport(source_id="fake-source", status="ok", created=1)
        report.created_vacancy_ids = [vac_id]
        return [report]

    monkeypatch.setattr("app.scheduler.jobs.scan_company", _fake_scan_company)

    db = S()
    try:
        run = run_job(db, "scan_due_companies")
    finally:
        db.close()

    assert run.status == "success"
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "new_jobs"]
    assert len(notes) == 1
    assert "Retail Assistant" in notes[0]["body"]


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
