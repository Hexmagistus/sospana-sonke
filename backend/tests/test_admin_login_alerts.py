"""When a client signs in, admins get an in-app notice. No client alert, no per-login email."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User
from app.notifications.email import ConsoleEmailProvider
from app.services.admin_login_alerts import send_login_digest
from tests.conftest import make_admin, register_and_login, admin_login

PW = "Password123!"


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _admin(client, db_engine, email="admin@example.com"):
    e, p = make_admin(db_engine, email=email)
    return admin_login(client, e, p).json()


def _notes(client, tokens, kind="client_login"):
    return [n for n in client.get("/api/v1/notifications", headers=_auth(tokens)).json()
            if n["type"] == kind]


def test_client_login_notifies_every_admin_in_app_only(client, db_engine, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", "owner@example.com")
    a1 = _admin(client, db_engine)
    a2 = _admin(client, db_engine, email="admin2@example.com")
    reg, tokens = register_and_login(client, email="thandi@example.com")
    ConsoleEmailProvider.outbox.clear()

    r = client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": PW})
    assert r.status_code == 200
    for adm in (a1, a2):
        [n] = _notes(client, adm)
        assert "Thandi Mokoena" in n["title"]
        assert n["link_url"] == "/admin"          # clickable: goes to the admin page
        assert n["email_sent"] is False
    # Not client facing, and no per-login email to the owner either.
    assert _notes(client, tokens) == []
    assert ConsoleEmailProvider.outbox == []


def test_one_notice_per_client_per_day_and_admin_logins_are_ignored(client, db_engine):
    admin = _admin(client, db_engine)
    register_and_login(client, email="busy@example.com")
    for _ in range(3):
        client.post("/api/v1/auth/login", json={"email": "busy@example.com", "password": PW})
    # register_and_login already logged in once; all four are the same day.
    assert len(_notes(client, admin)) == 1
    before = len(_notes(client, admin))
    admin_login(client, "admin@example.com", "AdminPass123!")
    assert len(_notes(client, admin)) == before


def test_failed_login_makes_no_notice(client, db_engine):
    admin = _admin(client, db_engine)
    s = sessionmaker(bind=db_engine)()
    try:
        from app.core import security
        s.add(User(email="x@example.com", password_hash=security.hash_password(PW),
                   first_name="X", last_name="Y"))
        s.commit()
    finally:
        s.close()
    client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass-123"})
    assert _notes(client, admin) == []


def test_legacy_per_login_email_is_off_by_default():
    assert settings.LOGIN_ALERTS_ENABLED is False


def test_digest_setting_is_admin_only_and_off_by_default(client, db_engine):
    admin = _admin(client, db_engine)
    _, tokens = register_and_login(client, email="c@example.com")
    assert client.get("/api/v1/admin/login-alerts", headers=_auth(tokens)).status_code == 403
    assert client.put("/api/v1/admin/login-alerts", headers=_auth(tokens),
                      json={"email_digest": True}).status_code == 403
    assert client.get("/api/v1/admin/login-alerts", headers=_auth(admin)).json() == {"email_digest": False}
    on = client.put("/api/v1/admin/login-alerts", headers=_auth(admin), json={"email_digest": True})
    assert on.json() == {"email_digest": True}
    assert client.get("/api/v1/admin/login-alerts", headers=_auth(admin)).json()["email_digest"] is True


def test_digest_goes_only_to_opted_in_admins_and_only_once(client, db_engine):
    on = _admin(client, db_engine)
    off = _admin(client, db_engine, email="off@example.com")
    client.put("/api/v1/admin/login-alerts", headers=_auth(on), json={"email_digest": True})
    register_and_login(client, email="a-client@example.com")
    ConsoleEmailProvider.outbox.clear()

    s = sessionmaker(bind=db_engine)()
    try:
        # switching it on starts from "now"; pretend that was yesterday
        me = s.query(User).filter(User.email == "admin@example.com").one()
        me.admin_login_digest_sent_at = datetime.now(timezone.utc) - timedelta(days=1)
        s.commit()
        res = send_login_digest(s)
        assert res == {"sent": 1, "clients": 1}
        again = send_login_digest(s)
        assert again == {"sent": 0, "clients": 0}
    finally:
        s.close()
    mails = ConsoleEmailProvider.outbox
    assert [m["to"] for m in mails] == ["admin@example.com"]
    assert "Thandi Mokoena" in mails[0]["body"]
    assert "a-client@example.com" not in mails[0]["body"]       # names, not addresses
    assert "off@example.com" not in [m["to"] for m in mails]


def test_digest_with_nothing_new_sends_nothing(client, db_engine):
    admin = _admin(client, db_engine)
    client.put("/api/v1/admin/login-alerts", headers=_auth(admin), json={"email_digest": True})
    ConsoleEmailProvider.outbox.clear()
    s = sessionmaker(bind=db_engine)()
    try:
        assert send_login_digest(s) == {"sent": 0, "clients": 0}
    finally:
        s.close()
    assert ConsoleEmailProvider.outbox == []


def test_digest_endpoint_and_job_registered(client, db_engine):
    from app.scheduler.registry import JOBS
    assert "send_admin_login_digest" in JOBS
    admin = _admin(client, db_engine)
    r = client.post("/api/v1/admin/login-alerts/digest", headers=_auth(admin))
    assert r.status_code == 200 and r.json()["sent"] is False
