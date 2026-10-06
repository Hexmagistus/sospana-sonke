"""Tests for notifications and the admin scheduler."""
import json
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


def _new_jobs_note(client, db_engine, tokens, job_run_id="run-0"):
    from app.services.notification_service import notify_new_jobs_broadcast
    from sqlalchemy.orm import sessionmaker
    vac_id = _seed_vacancy(db_engine)
    db = sessionmaker(bind=db_engine)()
    try:
        notify_new_jobs_broadcast(db, vacancy_ids=[vac_id], job_run_id=job_run_id)
        db.commit()
    finally:
        db.close()


def test_no_match_notifications_and_old_ones_are_hidden(client, db_engine):
    """Matching is gone: running it is 410, nothing is notified, and a leftover
    strong_match / daily_agent_briefing row from before the removal is never shown or counted."""
    from sqlalchemy.orm import sessionmaker
    from app.models.notification import Notification
    reg, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    assert client.post("/api/v1/matches/run", headers=_auth(tokens)).status_code == 410
    before = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert not any(n["type"] in ("strong_match", "daily_agent_briefing") for n in before)
    unread_before = client.get("/api/v1/notifications/unread-count", headers=_auth(tokens)).json()["unread"]

    db = sessionmaker(bind=db_engine)()
    try:
        for kind in ("strong_match", "daily_agent_briefing"):
            db.add(Notification(user_id=reg["user"]["id"], type=kind, title="old", body="old"))
        db.commit()
        assert db.query(Notification).filter(
            Notification.type.in_(("strong_match", "daily_agent_briefing"))).count() == 2   # untouched
    finally:
        db.close()
    after = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert [n["id"] for n in after] == [n["id"] for n in before]
    assert client.get("/api/v1/notifications/unread-count", headers=_auth(tokens)).json()["unread"] == unread_before


def test_mark_read_flow(client, db_engine):
    _, tokens = register_and_login(client)
    _new_jobs_note(client, db_engine, tokens)
    note = client.get("/api/v1/notifications", headers=_auth(tokens)).json()[0]
    assert client.get("/api/v1/notifications/unread-count", headers=_auth(tokens)).json()["unread"] >= 1
    assert client.post(f"/api/v1/notifications/{note['id']}/read", headers=_auth(tokens)).json()["is_read"] is True
    client.post("/api/v1/notifications/read-all", headers=_auth(tokens))
    assert client.get("/api/v1/notifications/unread-count", headers=_auth(tokens)).json()["unread"] == 0


def test_action_required_notification(client, db_engine):
    from tests.helpers_apps import make_application
    _, tokens = register_and_login(client)
    client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "assisted", "auto_apply_enabled": False, "min_match_score": 0,
        "max_applications_per_day": 5, "max_applications_per_week": 25,
        "excluded_companies": [], "excluded_roles": []})
    app_id = make_application(client, tokens, db_engine)
    client.post(f"/api/v1/applications/{app_id}/approve", headers=_auth(tokens))
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert any(n["type"] == "action_required" for n in notes)


def test_report_ready_notification(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
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


def test_scan_due_companies_does_not_broadcast_to_candidates(client, db_engine, monkeypatch):
    """scan_due_companies deliberately skips the "N new jobs" candidate broadcast
    (unlike scan_all_companies): NOTIFY_EMAILS is on in production, and that
    broadcast emails every active candidate synchronously, one HTTP call each,
    inside the same request -- with even a couple hundred candidates that alone
    can run minutes past this job's own time budget, which is the whole point of
    it being a small, frequent rotating-batch job. See its docstring."""
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

    def _fake_fetch(snapshot, client, now=None):
        return scan_service_module.FetchOutcome(kind="ok", started=0.0, now=now)

    def _fake_apply(db, source, outcome):
        report = scan_service_module.ScanReport(source_id=source.id, status="ok", created=1)
        report.created_vacancy_ids = [vac_id]
        return report

    monkeypatch.setattr("app.services.scan_batch._default_fetch", _fake_fetch)
    monkeypatch.setattr("app.services.scan_batch.apply_fetch", _fake_apply)

    db = S()
    try:
        run = run_job(db, "scan_due_companies")
    finally:
        db.close()

    assert run.status == "success"
    detail = json.loads(run.detail)
    assert detail["vacancies_created"] >= 1
    assert detail["candidates_alerted"] == 0
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "new_jobs"]
    assert len(notes) == 0


# ---- scheduler (admin) ----

def _admin(client, db_engine):
    email, password = make_admin(db_engine)
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()


def test_schedule_defaults_and_update(client, db_engine):
    admin = _admin(client, db_engine)
    got = client.get("/api/v1/admin/schedule", headers=_auth(admin)).json()["schedule"]
    assert "scan_all_companies" in got and "match_all_candidates" not in got

    upd = client.put("/api/v1/admin/schedule", headers=_auth(admin),
                     json={"schedule": {"scan_all_companies": "0 */12 * * *"}}).json()["schedule"]
    assert upd["scan_all_companies"] == "0 */12 * * *"


def test_schedule_requires_admin(client):
    _, tokens = register_and_login(client)
    assert client.get("/api/v1/admin/schedule", headers=_auth(tokens)).status_code == 403


def test_trigger_job_and_run_log(client, db_engine):
    admin = _admin(client, db_engine)
    run = client.post("/api/v1/admin/jobs/close_expired_vacancies/run", headers=_auth(admin))
    assert run.status_code == 200 and run.json()["status"] == "success"
    runs = client.get("/api/v1/admin/jobs/runs", headers=_auth(admin)).json()
    assert any(r["job_name"] == "close_expired_vacancies" for r in runs)


def test_retired_matching_jobs_still_answer_harmlessly(client, db_engine):
    """cron-job.org may still call match_all_candidates / run_daily_agent by name: both answer
    200 'disabled', create no match or notification, and need no data."""
    from sqlalchemy.orm import sessionmaker
    from app.models.match import CandidateMatch
    from app.models.notification import Notification
    admin = _admin(client, db_engine)
    _, tokens = register_and_login(client, email="cand-disabled@example.com")
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    for name in ("match_all_candidates", "run_daily_agent"):
        r = client.post(f"/api/v1/admin/jobs/{name}/run", headers=_auth(admin))
        assert r.status_code == 200 and r.json()["status"] == "success", name
        assert json.loads(r.json()["detail"])["status"] == "disabled", name
    db = sessionmaker(bind=db_engine)()
    try:
        assert db.query(CandidateMatch).count() == 0
        assert db.query(Notification).filter(Notification.type.in_(
            ("strong_match", "daily_agent_briefing"))).count() == 0
    finally:
        db.close()


def test_trigger_unknown_job(client, db_engine):
    admin = _admin(client, db_engine)
    assert client.post("/api/v1/admin/jobs/nope/run", headers=_auth(admin)).status_code == 404


# ---- admin: suggest a post/link to relevant candidates ----

def test_admin_can_suggest_to_specific_candidates(client, db_engine):
    admin = _admin(client, db_engine)
    reg, tokens = register_and_login(
        client, email="candidate1@example.com",
        preferred_position="Process Controller", notify_opportunity_alerts=True,
    )
    candidate_id = reg["user"]["id"]

    resp = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json={
        "title": "Worth a read", "body": "This article matches your field.",
        "link_url": "https://example.com/article", "user_ids": [candidate_id],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["sent"] == 1
    assert resp.json()["skipped"] == 0

    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "admin_suggestion"]
    assert len(notes) == 1
    assert notes[0]["title"] == "Worth a read"
    assert notes[0]["link_url"] == "https://example.com/article"


def test_admin_suggestion_to_all_candidates(client, db_engine):
    admin = _admin(client, db_engine)
    _, tokens_a = register_and_login(
        client, email="candidatea@example.com",
        preferred_position="Nurse", notify_opportunity_alerts=True,
    )
    _, tokens_b = register_and_login(
        client, email="candidateb@example.com",
        preferred_position="Teacher", notify_opportunity_alerts=True,
    )

    resp = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json={
        "title": "New guide for everyone", "body": "Check this out.",
        "all_candidates": True,
    })
    assert resp.status_code == 200
    assert resp.json()["sent"] == 2
    assert resp.json()["skipped"] == 0

    for t in (tokens_a, tokens_b):
        notes = [n for n in client.get("/api/v1/notifications", headers=_auth(t)).json()
                 if n["type"] == "admin_suggestion"]
        assert len(notes) == 1
        assert notes[0]["link_url"] is None


def test_admin_suggestion_stores_an_in_app_notice_without_an_email_choice(client, db_engine):
    """A selected person with no recorded choice gets the notice, and no email."""
    admin = _admin(client, db_engine)
    reg, tokens = register_and_login(
        client, email="quiet@example.com", preferred_position="Driver",
    )
    resp = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json={
        "title": "A matching post", "body": "Inside your account.",
        "link_url": "https://example.com/driver",
        "user_ids": [reg["user"]["id"]],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["sent"] == 1
    assert resp.json()["skipped"] == 0
    assert resp.json()["emailed"] == 0
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "admin_suggestion"]
    assert len(notes) == 1
    assert notes[0]["email_sent"] is False

    broadcast = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json={
        "title": "Everyone", "body": "Only people who opted in.",
        "all_candidates": True,
    })
    assert broadcast.status_code == 200, broadcast.text
    assert broadcast.json()["sent"] == 0
    assert broadcast.json()["skipped"] == 1


def test_admin_suggestion_requires_admin(client, db_engine):
    _, tokens = register_and_login(client)
    resp = client.post("/api/v1/admin/suggestions", headers=_auth(tokens), json={
        "title": "x", "body": "y", "all_candidates": True,
    })
    assert resp.status_code == 403


def test_admin_suggestion_requires_a_target(client, db_engine):
    admin = _admin(client, db_engine)
    resp = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json={
        "title": "x", "body": "y",
    })
    assert resp.status_code == 400


def test_admin_suggestion_rejects_non_http_link(client, db_engine):
    admin = _admin(client, db_engine)
    for link in ("javascript:alert(1)", "data:text/html,hi", "https://user:pass@example.com/jobs", "http://"):
        resp = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json={
            "title": "x", "body": "y", "link_url": link, "all_candidates": True,
        })
        assert resp.status_code == 422, link


def test_suggestion_notice_includes_the_link_and_is_not_repeated(client, db_engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.company import Company
    from app.models.vacancy import Vacancy, VacancySource
    from app.notifications.email import ConsoleEmailProvider, _html_from_text

    monkeypatch.setattr(settings, "NOTIFY_EMAILS", True)
    admin = _admin(client, db_engine)
    reg, tokens = register_and_login(
        client, email="tagged@example.com",
        preferred_position="Nurse", notify_opportunity_alerts=True, allow_tagging=True,
    )
    quiet, quiet_tokens = register_and_login(
        client, email="quiet-tag@example.com", preferred_position="Nurse",
    )
    now = datetime.now(timezone.utc)
    session = sessionmaker(bind=db_engine)()
    try:
        company = Company(company_name="Acme Logistics", country="South Africa",
                          careers_url="https://acme.example/careers")
        session.add(company)
        session.commit()
        session.refresh(company)
        source = VacancySource(company_id=company.id, url=company.careers_url, ats_type="static")
        session.add(source)
        session.commit()
        session.refresh(source)
        session.add(Vacancy(
            company_id=company.id, source_id=source.id, title="Ward Nurse",
            application_url="https://apply.example.com/nurse",
            content_hash="nurse-hash", is_open=True, first_seen_at=now, last_seen_at=now,
        ))
        session.commit()
    finally:
        session.close()

    ConsoleEmailProvider.outbox.clear()
    link = "https://apply.example.com/nurse"
    payload = {
        "title": "A ward role",
        "body": "This matches the post you saved.",
        "link_url": link,
        "user_ids": [reg["user"]["id"], quiet["user"]["id"]],
    }
    first = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["sent"] == 2
    assert first.json()["skipped"] == 0
    assert first.json()["duplicates"] == 0
    assert first.json()["emailed"] == 0   # never one by one: the daily digest carries it

    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "admin_suggestion"]
    assert len(notes) == 1
    assert notes[0]["link_url"] == link
    assert notes[0]["email_sent"] is False
    assert "Tagged by the Sospana Sonke team." in notes[0]["body"]
    assert "Role: Ward Nurse" in notes[0]["body"]
    assert "Employer: Acme Logistics" in notes[0]["body"]
    assert link in notes[0]["body"]
    assert "Tagged at " in notes[0]["body"]
    assert not [m for m in ConsoleEmailProvider.outbox if link in m["body"]]
    html = _html_from_text(notes[0]["body"])
    assert f'href="{link}"' in html
    assert "Open this listing" in html
    assert "<script>" not in html
    quiet_notes = [n for n in client.get("/api/v1/notifications", headers=_auth(quiet_tokens)).json()
                   if n["type"] == "admin_suggestion"]
    assert len(quiet_notes) == 1
    assert quiet_notes[0]["email_sent"] is False
    assert link in quiet_notes[0]["body"]

    second = client.post("/api/v1/admin/suggestions", headers=_auth(admin), json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["sent"] == 0
    assert second.json()["duplicates"] == 2
    again = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "admin_suggestion"]
    assert len(again) == 1
    assert not [m for m in ConsoleEmailProvider.outbox if link in m["body"]]


def test_tagging_with_a_link_sends_one_notice(client, db_engine):
    admin = _admin(client, db_engine)
    reg, tokens = register_and_login(
        client, email="tag-link@example.com",
        preferred_position="Chef", notify_opportunity_alerts=True, allow_tagging=True,
    )
    user_id = reg["user"]["id"]
    blocked = client.post(
        f"/api/v1/admin/users/{user_id}/tags", headers=_auth(admin),
        json={"tag": "kitchen", "link_url": "javascript:alert(1)"},
    )
    assert blocked.status_code == 422
    listed = client.get("/api/v1/admin/users", headers=_auth(admin)).json()
    row = next(r for r in listed if r["id"] == user_id)
    assert row["tags"] == []

    ok = client.post(
        f"/api/v1/admin/users/{user_id}/tags", headers=_auth(admin),
        json={"tag": "kitchen", "link_url": "https://acme.example/careers"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["notice_sent"] == 1
    assert "kitchen" in ok.json()["tags"]
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "admin_suggestion"]
    assert len(notes) == 1
    assert notes[0]["link_url"] == "https://acme.example/careers"
    assert notes[0]["title"] == "kitchen"
    assert "Tagged by the Sospana Sonke team." in notes[0]["body"]

    repeat = client.post(
        f"/api/v1/admin/users/{user_id}/tags", headers=_auth(admin),
        json={"tag": "kitchen", "link_url": "https://acme.example/careers"},
    )
    assert repeat.status_code == 200, repeat.text
    assert repeat.json()["notice_duplicate"] == 1
    assert repeat.json()["notice_sent"] == 0
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
             if n["type"] == "admin_suggestion"]
    assert len(notes) == 1


def test_cron_endpoint_for_retired_matching_job_returns_disabled_not_error(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "CRON_SECRET", "s3cret")
    for name in ("match_all_candidates", "run_daily_agent"):
        r = client.post(f"/api/v1/cron/run/{name}", headers={"X-Cron-Secret": "s3cret"})
        assert r.status_code == 200, (name, r.text)
        assert r.json()["status"] == "success" and json.loads(r.json()["detail"])["status"] == "disabled"
