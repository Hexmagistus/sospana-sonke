"""Owner gets an email every time someone signs in."""
from app.core.config import settings
from app.notifications.email import ConsoleEmailProvider


def _register(client, email="thandi@example.com"):
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "StrongPass123!", "first_name": "Thandi", "last_name": "Mokoena",
        "accepted_policy": True})
    assert r.status_code == 201, r.text


def _alerts(to):
    return [m for m in ConsoleEmailProvider.outbox if m["to"] == to and "login" in m["subject"]]


def test_login_emails_owner(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", "owner@example.com")
    ConsoleEmailProvider.outbox.clear()
    _register(client)
    assert _alerts("owner@example.com") == []          # registering alone is not a login
    r = client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": "StrongPass123!"},
                    headers={"X-Forwarded-For": "41.13.2.9, 10.0.0.1", "User-Agent": "TestPhone/1.0"})
    assert r.status_code == 200
    [msg] = _alerts("owner@example.com")
    assert "Thandi Mokoena" in msg["subject"]
    for part in ("thandi@example.com", "email & password", "41.13.2.9", "TestPhone/1.0", "SAST"):
        assert part in msg["body"]


def test_failed_login_sends_nothing(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", "owner@example.com")
    _register(client)
    ConsoleEmailProvider.outbox.clear()
    r = client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": "wrong-pass-123"})
    assert r.status_code == 401
    assert _alerts("owner@example.com") == []


def test_multiple_recipients_and_fallback(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", "a@example.com, b@example.com")
    _register(client)
    ConsoleEmailProvider.outbox.clear()
    client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": "StrongPass123!"})
    assert len(_alerts("a@example.com")) == 1 and len(_alerts("b@example.com")) == 1

    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", None)
    monkeypatch.setattr(settings, "SMTP_USER", "sender@gmail.com")
    ConsoleEmailProvider.outbox.clear()
    client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": "StrongPass123!"})
    assert len(_alerts("sender@gmail.com")) == 1


def test_alerts_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", "owner@example.com")
    monkeypatch.setattr(settings, "LOGIN_ALERTS_ENABLED", False)
    _register(client)
    ConsoleEmailProvider.outbox.clear()
    r = client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": "StrongPass123!"})
    assert r.status_code == 200
    assert _alerts("owner@example.com") == []


def test_email_failure_does_not_break_login(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", "owner@example.com")
    _register(client)

    def boom(self, to, subject, body):
        raise RuntimeError("SMTP down")
    monkeypatch.setattr(ConsoleEmailProvider, "send", boom)
    r = client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": "StrongPass123!"})
    assert r.status_code == 200 and r.json()["access_token"]
