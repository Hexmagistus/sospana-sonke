"""Tests for SMS/push notification channels and admin analytics."""
from datetime import datetime, timezone

from tests.conftest import register_and_login, make_admin
from app.core.config import settings
from app.notifications.channels import ConsoleSMSProvider, ConsolePushProvider
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancyRequirement


def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def _seed_and_match(client, tokens, db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine); s = S()
    try:
        c = Company(company_name="Acme Logistics", sector="Logistics",
                    careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title="Operations Manager", location="Johannesburg",
                    description="SQL needed.", application_url="https://apply.example/1",
                    content_hash="h1", is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        s.add(VacancyRequirement(vacancy_id=v.id, text="Minimum of 5 years experience required",
                                 kind="hard", category="experience"))
        s.commit()
    finally:
        s.close()
    h = _auth(tokens)
    client.put("/api/v1/profile", headers=h, json={"years_experience": 6,
               "desired_occupations": ["Operations Manager"], "industries": ["logistics"],
               "preferred_locations": ["Johannesburg"]})
    client.post("/api/v1/profile/skills", headers=h, json={"name": "SQL", "category": "technical"})
    client.post("/api/v1/matches/run", headers=h)
    return client.get("/api/v1/matches", headers=h).json()[0]["id"]


def test_sms_channel_on_strong_match(client, db_engine, monkeypatch):
    ConsoleSMSProvider.outbox.clear()
    monkeypatch.setattr(settings, "NOTIFY_SMS", True)
    _, tokens = register_and_login(client)   # conftest sets mobile_number 0821234567
    _seed_and_match(client, tokens, db_engine)

    assert any(m["to"] == "0821234567" for m in ConsoleSMSProvider.outbox)
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    strong = next(n for n in notes if n["type"] == "strong_match")
    assert strong["sms_sent"] is True


def test_push_channel_with_registered_token(client, db_engine, monkeypatch):
    ConsolePushProvider.outbox.clear()
    _, tokens = register_and_login(client)
    reg = client.post("/api/v1/notifications/push-tokens", headers=_auth(tokens),
                      json={"token": "device-abc", "platform": "web"})
    assert reg.status_code == 201

    monkeypatch.setattr(settings, "NOTIFY_PUSH", True)
    _seed_and_match(client, tokens, db_engine)

    assert any(p["token"] == "device-abc" for p in ConsolePushProvider.outbox)
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert any(n["type"] == "strong_match" and n["push_sent"] for n in notes)


def test_channels_off_by_default(client, db_engine):
    ConsoleSMSProvider.outbox.clear()
    _, tokens = register_and_login(client)
    _seed_and_match(client, tokens, db_engine)
    # Defaults: NOTIFY_SMS / NOTIFY_PUSH False -> nothing sent on those channels.
    assert ConsoleSMSProvider.outbox == []
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert all(n["sms_sent"] is False for n in notes)


# ---- analytics ----

def test_admin_analytics_requires_admin(client):
    _, tokens = register_and_login(client)
    assert client.get("/api/v1/admin/analytics", headers=_auth(tokens)).status_code == 403


def test_admin_analytics_funnel(client, db_engine):
    _, tokens = register_and_login(client, email="cand@example.com")
    match_id = _seed_and_match(client, tokens, db_engine)
    app = client.post(f"/api/v1/matches/{match_id}/prepare-application", headers=_auth(tokens)).json()
    client.post(f"/api/v1/applications/{app['id']}/approve", headers=_auth(tokens))
    client.post(f"/api/v1/applications/{app['id']}/mark-submitted", headers=_auth(tokens))
    client.post(f"/api/v1/applications/{app['id']}/status", headers=_auth(tokens), json={"status": "INTERVIEW"})

    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    a = client.get("/api/v1/admin/analytics", headers=_auth(admin))
    assert a.status_code == 200
    body = a.json()
    assert body["funnel"]["matches"] >= 1 and body["funnel"]["submitted"] >= 1
    assert body["funnel"]["interviews"] >= 1
    assert body["rates"]["interview_rate"] > 0
    assert body["top_companies_by_matches"][0]["company"] == "Acme Logistics"
