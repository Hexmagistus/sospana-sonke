"""Tests for SMS/push notification channels and admin analytics."""

from tests.conftest import register_and_login, make_admin, admin_login
from app.core.config import settings
from app.notifications.channels import ConsoleSMSProvider, ConsolePushProvider


def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def _approve_application(client, tokens, db_engine):
    """Approving an application creates an 'action_required' notification (matching is gone,
    so this is the in-app notification the SMS/push channels are exercised with)."""
    from tests.helpers_apps import make_application
    h = _auth(tokens)
    client.put("/api/v1/preferences", headers=h, json={
        "application_mode": "assisted", "auto_apply_enabled": False, "min_match_score": 0,
        "max_applications_per_day": 5, "max_applications_per_week": 25,
        "excluded_companies": [], "excluded_roles": []})
    app_id = make_application(client, tokens, db_engine)
    r = client.post(f"/api/v1/applications/{app_id}/approve", headers=h)
    assert r.status_code == 200, r.text


def test_sms_channel_on_action_required(client, db_engine, monkeypatch):
    ConsoleSMSProvider.outbox.clear()
    monkeypatch.setattr(settings, "NOTIFY_SMS", True)
    _, tokens = register_and_login(client)   # conftest sets mobile_number 0821234567
    _approve_application(client, tokens, db_engine)

    assert any(m["to"] == "0821234567" for m in ConsoleSMSProvider.outbox)
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    note = next(n for n in notes if n["type"] == "action_required")
    assert note["sms_sent"] is True


def test_push_channel_with_registered_token(client, db_engine, monkeypatch):
    ConsolePushProvider.outbox.clear()
    _, tokens = register_and_login(client)
    reg = client.post("/api/v1/notifications/push-tokens", headers=_auth(tokens),
                      json={"token": "device-abc", "platform": "web"})
    assert reg.status_code == 201

    monkeypatch.setattr(settings, "NOTIFY_PUSH", True)
    _approve_application(client, tokens, db_engine)

    assert any(p["token"] == "device-abc" for p in ConsolePushProvider.outbox)
    notes = client.get("/api/v1/notifications", headers=_auth(tokens)).json()
    assert any(n["type"] == "action_required" and n["push_sent"] for n in notes)


def test_channels_off_by_default(client, db_engine):
    ConsoleSMSProvider.outbox.clear()
    _, tokens = register_and_login(client)
    _approve_application(client, tokens, db_engine)
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
    from tests.helpers_apps import make_application
    app_id = make_application(client, tokens, db_engine)
    client.post(f"/api/v1/applications/{app_id}/approve", headers=_auth(tokens))
    client.post(f"/api/v1/applications/{app_id}/mark-submitted", headers=_auth(tokens))
    client.post(f"/api/v1/applications/{app_id}/status", headers=_auth(tokens), json={"status": "INTERVIEW"})

    email, password = make_admin(db_engine)
    admin = admin_login(client, email, password).json()
    a = client.get("/api/v1/admin/analytics", headers=_auth(admin))
    assert a.status_code == 200
    body = a.json()
    assert "matches" not in body["funnel"] and "top_companies_by_matches" not in body
    assert body["funnel"]["submitted"] >= 1
    assert body["funnel"]["interviews"] >= 1
    assert body["rates"]["interview_rate"] > 0
