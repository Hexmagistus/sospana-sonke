"""Tagging email is a recorded choice. No choice is not a yes and not a no."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.admin_ops import AdminAuditLog
from app.models.user import User
from app.notifications.email import ConsoleEmailProvider
from app.services.tagging_pref_mail import (
    _FORBIDDEN,
    preferences_url,
    service_email_body,
)
from tests.conftest import make_admin, register_and_login


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _admin(client, db_engine):
    email, password = make_admin(db_engine)
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()


def test_service_email_names_us_and_has_no_listing_words():
    body = service_email_body()
    low = body.lower()
    assert "Sospana Sonke" in body
    assert "Choose or turn off" in body
    assert preferences_url() in body
    assert preferences_url().endswith("/security#notification-preferences")
    assert not any(word in low for word in _FORBIDDEN)


def test_existing_account_with_no_choice_sees_the_banner_until_they_dismiss_or_choose(client):
    reg, tokens = register_and_login(client, email="unset-banner@example.com")
    me = client.get("/api/v1/auth/me", headers=_auth(tokens)).json()
    assert me["tagging_email"] is None
    assert me["show_tagging_banner"] is True
    assert me["notify_opportunity_alerts"] is False

    dismissed = client.post("/api/v1/account/tagging-banner/dismiss", headers=_auth(tokens))
    assert dismissed.status_code == 200
    assert dismissed.json()["show_tagging_banner"] is False
    still = client.get("/api/v1/auth/me", headers=_auth(tokens)).json()
    assert still["tagging_email"] is None
    assert still["show_tagging_banner"] is False

    chosen = client.put(
        "/api/v1/account/notification-preferences",
        headers=_auth(tokens),
        json={"preferred_position": "Nurse", "tagging_email": False, "record_tagging_email": True},
    )
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["tagging_email"] is False
    assert chosen.json()["preferred_position"] == "Nurse"
    assert chosen.json()["show_tagging_banner"] is False

    exported = client.get("/api/v1/account/export", headers=_auth(tokens)).json()
    assert exported["account"]["tagging_email"] is False
    assert exported["account"]["tagging_email_chosen_at"]


def test_register_records_an_explicit_no_and_hides_the_banner(client):
    reg, tokens = register_and_login(client, email="explicit-no@example.com", tagging_email=False)
    assert reg["user"]["tagging_email"] is False
    assert reg["user"]["show_tagging_banner"] is False
    me = client.get("/api/v1/auth/me", headers=_auth(tokens)).json()
    assert me["tagging_email"] is False


def test_saving_the_preferred_post_does_not_invent_an_email_choice(client):
    _, tokens = register_and_login(client, email="post-only@example.com", preferred_position="Driver")
    saved = client.put(
        "/api/v1/account/notification-preferences",
        headers=_auth(tokens),
        json={"preferred_position": "Cook", "notify_opportunity_alerts": True},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["preferred_position"] == "Cook"
    assert body["notify_opportunity_alerts"] is True
    assert body["tagging_email"] is None


def test_service_email_counts_first_then_sends_once(client, db_engine, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFY_EMAILS", False)
    admin = _admin(client, db_engine)
    register_and_login(client, email="needs-choice@example.com")
    register_and_login(client, email="already-no@example.com", tagging_email=False)
    register_and_login(client, email="already-yes@example.com", tagging_email=True)
    ConsoleEmailProvider.outbox.clear()

    counted = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(admin),
        json={"dry_run": True, "batch": 40},
    )
    assert counted.status_code == 200, counted.text
    assert counted.json()["eligible"] == 1
    assert counted.json()["would_send"] == 1
    assert counted.json()["sent"] == 0
    assert ConsoleEmailProvider.outbox == []

    sent = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(admin),
        json={"dry_run": False, "batch": 40},
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["sent"] == 1
    mailed = [m for m in ConsoleEmailProvider.outbox if m["to"] == "needs-choice@example.com"]
    assert len(mailed) == 1
    assert "Sospana Sonke" in mailed[0]["body"]
    assert preferences_url() in mailed[0]["body"]
    assert not any(word in mailed[0]["body"].lower() for word in _FORBIDDEN)

    again = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(admin),
        json={"dry_run": False, "batch": 40},
    )
    assert again.status_code == 200, again.text
    assert again.json()["sent"] == 0
    assert again.json()["eligible"] == 0
    assert len([m for m in ConsoleEmailProvider.outbox if m["to"] == "needs-choice@example.com"]) == 1

    session = sessionmaker(bind=db_engine)()
    try:
        audits = session.query(AdminAuditLog).filter(AdminAuditLog.action == "tagging_pref_email").all()
        assert audits
        assert all("@" not in (row.detail or "") for row in audits)
    finally:
        session.close()


def test_service_email_stops_at_the_daily_cap_and_resumes_the_next_day(client, db_engine, monkeypatch):
    monkeypatch.setattr("app.services.tagging_pref_mail.TAGGING_PREF_DAILY_CAP", 1)
    admin = _admin(client, db_engine)
    register_and_login(client, email="first-cap@example.com")
    register_and_login(client, email="second-cap@example.com")
    ConsoleEmailProvider.outbox.clear()

    first = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(admin),
        json={"dry_run": False, "batch": 40},
    )
    assert first.status_code == 200, first.text
    assert first.json()["sent"] == 1

    blocked = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(admin),
        json={"dry_run": True, "batch": 40},
    )
    assert blocked.json()["eligible"] == 1
    assert blocked.json()["remaining_today"] == 0
    assert blocked.json()["would_send"] == 0
    assert blocked.json()["resume_on"]

    session = sessionmaker(bind=db_engine)()
    try:
        stamped = (session.query(User)
                   .filter(User.tagging_pref_service_sent_at.isnot(None))
                   .one())
        stamped.tagging_pref_service_sent_at = datetime.now(timezone.utc) - timedelta(days=1)
        session.commit()
    finally:
        session.close()

    resumed = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(admin),
        json={"dry_run": False, "batch": 40},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["sent"] == 1
    assert resumed.json()["eligible"] == 0


def test_a_failed_send_is_not_recorded_as_delivered(client, db_engine, monkeypatch):
    admin = _admin(client, db_engine)
    register_and_login(client, email="retry-me@example.com")

    def _fail(self, to, subject, body):
        return False

    monkeypatch.setattr(ConsoleEmailProvider, "send", _fail)
    failed = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(admin),
        json={"dry_run": False, "batch": 40},
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["sent"] == 0
    assert failed.json()["eligible"] == 1


def test_service_email_requires_an_admin(client):
    _, tokens = register_and_login(client, email="not-admin@example.com")
    denied = client.post(
        "/api/v1/admin/tagging-preference-email",
        headers=_auth(tokens),
        json={"dry_run": True},
    )
    assert denied.status_code == 403


def test_inactive_account_cannot_be_tagged(client, db_engine):
    admin = _admin(client, db_engine)
    reg, _ = register_and_login(client, email="inactive-tag@example.com")
    session = sessionmaker(bind=db_engine)()
    try:
        person = session.get(User, reg["user"]["id"])
        person.is_active = False
        session.commit()
    finally:
        session.close()
    denied = client.post(
        f"/api/v1/admin/users/{reg['user']['id']}/tags",
        headers=_auth(admin),
        json={"tag": "kitchen"},
    )
    assert denied.status_code == 403


def test_delete_clears_the_tagging_choice(client, db_engine):
    reg, tokens = register_and_login(client, email="erase-choice@example.com", tagging_email=True)
    gone = client.post("/api/v1/account/delete", headers=_auth(tokens), json={"password": "Password123!"})
    assert gone.status_code == 204
    session = sessionmaker(bind=db_engine)()
    try:
        person = session.get(User, reg["user"]["id"])
        assert person.tagging_email is None
        assert person.tagging_email_chosen_at is None
        assert person.tagging_banner_seen_at is None
        assert person.tagging_pref_service_sent_at is None
    finally:
        session.close()
