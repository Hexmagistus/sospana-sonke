"""Gauteng Hustle Run tester-access requests: public form + admin export."""
from sqlalchemy import create_engine, inspect

from tests.conftest import make_admin, register_and_login

URL = "/api/v1/game/tester-requests"
ADMIN = "/api/v1/admin/game/tester-requests"


def _admin_headers(client, db_engine):
    email, password = make_admin(db_engine)
    tok = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    return {"Authorization": f"Bearer {tok['access_token']}"}


def test_submit_and_duplicate_is_success(client, db_engine):
    r = client.post(URL, json={"email": "  Thabo.M@Gmail.com ", "name": "Thabo"})
    assert r.status_code == 200, r.text
    assert "on the list" in r.json()["message"]
    again = client.post(URL, json={"email": "thabo.m@gmail.com"})
    assert again.status_code == 200
    h = _admin_headers(client, db_engine)
    rows = client.get(ADMIN, headers=h).json()
    assert [x["email"] for x in rows] == ["thabo.m@gmail.com"]
    assert rows[0]["name"] == "Thabo" and rows[0]["status"] == "pending"


def test_invalid_email_rejected(client):
    for bad in ["", "nope", "a@b", "a b@gmail.com", "x@@gmail.com", "<x>@gmail.com"]:
        assert client.post(URL, json={"email": bad}).status_code == 422, bad


def test_honeypot_stores_nothing(client, db_engine):
    r = client.post(URL, json={"email": "bot@example.com", "website": "http://spam"})
    assert r.status_code == 200
    h = _admin_headers(client, db_engine)
    assert client.get(ADMIN, headers=h).json() == []


def test_signed_in_user_is_linked(client, db_engine):
    _, tokens = register_and_login(client)
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    user = client.get("/api/v1/auth/me", headers=auth).json()
    r = client.post(URL, json={"email": user["email"]}, headers=auth)
    assert r.status_code == 200
    h = _admin_headers(client, db_engine)
    assert client.get(ADMIN, headers=h).json()[0]["user_id"] == user["id"]


def test_admin_routes_are_protected(client):
    assert client.get(ADMIN).status_code in (401, 403)
    assert client.get(ADMIN + "/export").status_code in (401, 403)
    assert client.post(ADMIN + "/mark-added", json={"all_pending": True}).status_code in (401, 403)
    _, tokens = register_and_login(client, email="plain@example.com")
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get(ADMIN + "/export", headers=h).status_code == 403


def test_export_and_mark_added(client, db_engine):
    for e in ["a@gmail.com", "b@gmail.com", "c@gmail.com"]:
        client.post(URL, json={"email": e})
    h = _admin_headers(client, db_engine)
    exp = client.get(ADMIN + "/export", headers=h)
    assert exp.status_code == 200
    assert exp.text.splitlines() == ["a@gmail.com", "b@gmail.com", "c@gmail.com"]
    assert exp.headers["content-type"].startswith("text/csv")
    r = client.post(ADMIN + "/mark-added", json={"emails": ["A@gmail.com"]}, headers=h)
    assert r.json() == {"updated": 1}
    assert client.get(ADMIN + "/export", headers=h).text.splitlines() == ["b@gmail.com", "c@gmail.com"]
    added = client.get(ADMIN, params={"status": "added"}, headers=h).json()
    assert added[0]["email"] == "a@gmail.com" and added[0]["added_at"]
    assert client.post(ADMIN + "/mark-added", json={"all_pending": True}, headers=h).json() == {"updated": 2}
    assert client.get(ADMIN + "/export", headers=h).text == ""


def test_migration_up_and_down(tmp_path):
    from app.db.base import Base
    from app import models  # noqa: F401
    from app.db.migrations.game_tester_requests import downgrade, upgrade
    eng = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    Base.metadata.tables["users"].create(eng)
    upgrade(eng)
    upgrade(eng)  # idempotent
    insp = inspect(eng)
    assert "game_tester_requests" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("game_tester_requests")}
    assert cols == {"id", "email", "name", "user_id", "created_at", "status", "added_at"}
    downgrade(eng)
    assert "game_tester_requests" not in inspect(eng).get_table_names()
