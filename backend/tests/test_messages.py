"""Temporary messaging: opt-in, filtering, block/report, expiry, and POPIA export/erasure."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from tests.conftest import register_and_login, make_admin
from app.models.message import Message, MessageReport
from app.models.user import User

API = "/api/v1"


def _h(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def _two_users(client):
    a = register_and_login(client, email="a@example.com")[1]
    b = register_and_login(client, email="b@example.com")[1]
    return a, b


def _id(client, t):
    return client.get(f"{API}/auth/me", headers=_h(t)).json()["id"]


def test_recipient_must_opt_in(client):
    a, b = _two_users(client)
    bid = _id(client, b)
    r = client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": "Hello there"})
    assert r.status_code == 404
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    r = client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": "Hello there"})
    assert r.status_code == 201
    inbox = client.get(f"{API}/messages/inbox", headers=_h(b)).json()
    assert len(inbox) == 1 and inbox[0]["body"] == "Hello there"
    assert "@" not in inbox[0]["other_name"]


def test_directory_only_lists_opted_in_users_without_email(client):
    a, b = _two_users(client)
    assert client.get(f"{API}/messages/directory?q=Th", headers=_h(a)).json() == []
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    rows = client.get(f"{API}/messages/directory?q=Th", headers=_h(a)).json()
    assert len(rows) == 1 and set(rows[0]) == {"id", "name"}


def test_filter_blocks_links_contacts_and_scams(client):
    a, b = _two_users(client)
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    bid = _id(client, b)
    for bad in ["see https://evil.example", "mail me x@y.com", "call 082 123 4567", "pay the processing fee"]:
        r = client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": bad})
        assert r.status_code == 422, bad


def test_block_stops_messages(client):
    a, b = _two_users(client)
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    aid, bid = _id(client, a), _id(client, b)
    assert client.post(f"{API}/messages/blocks/{aid}", headers=_h(b)).status_code == 204
    r = client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": "Hi"})
    assert r.status_code == 404


def test_report_snapshots_and_admin_can_suspend(client, db_engine):
    a, b = _two_users(client)
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    bid = _id(client, b)
    mid = client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": "Rude words"}).json()["id"]
    assert client.post(f"{API}/messages/{mid}/report", headers=_h(b),
                       json={"reason": "harassment"}).status_code == 201
    assert client.get(f"{API}/messages/inbox", headers=_h(b)).json() == []
    email, pw = make_admin(db_engine)
    admin = client.post(f"{API}/auth/login", json={"email": email, "password": pw}).json()
    reports = client.get(f"{API}/admin/message-reports", headers=_h(admin)).json()
    assert reports[0]["body_snapshot"] == "Rude words"
    res = client.post(f"{API}/admin/message-reports/{reports[0]['id']}/resolve", headers=_h(admin),
                      json={"action": "suspend_sender"})
    assert res.json()["sender_banned"] is True
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    r = client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": "Hi again"})
    assert r.status_code == 403


def test_messages_expire_after_24h(client, db_engine):
    a, b = _two_users(client)
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    bid = _id(client, b)
    client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": "Short lived"})
    S = sessionmaker(bind=db_engine); s = S()
    try:
        for m in s.query(Message).all():
            m.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        s.commit()
    finally:
        s.close()
    assert client.get(f"{API}/messages/inbox", headers=_h(b)).json() == []
    S = sessionmaker(bind=db_engine); s = S()
    try:
        assert s.query(Message).count() == 0
    finally:
        s.close()


def test_export_and_erasure(client, db_engine):
    a, b = _two_users(client)
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    bid = _id(client, b)
    client.post(f"{API}/messages", headers=_h(a), json={"recipient_id": bid, "body": "Keep me short"})
    data = client.get(f"{API}/account/export", headers=_h(b)).json()
    assert data["account"]["email"] == "b@example.com" and len(data["temporary_messages"]) == 1
    assert client.post(f"{API}/account/delete", headers=_h(b), json={"password": "wrong"}).status_code == 403
    assert client.post(f"{API}/account/delete", headers=_h(b), json={"password": "Password123!"}).status_code == 204
    S = sessionmaker(bind=db_engine); s = S()
    try:
        u = s.query(User).filter(User.id == bid).one()
        assert u.is_active is False and u.email.endswith("@deleted.invalid") and u.deleted_at is not None
        assert s.query(Message).count() == 0
    finally:
        s.close()
