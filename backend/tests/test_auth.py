"""Tests for authentication and access control."""
from tests.conftest import register_and_login


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_register_login_verify_me(client):
    reg, tokens = register_and_login(client)
    assert reg["user"]["email_verified"] is False
    assert tokens["access_token"] and tokens["refresh_token"]

    # /me with the access token
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "thandi@example.com"

    # verify email using the returned token
    v = client.get("/api/v1/auth/verify", params={"token": reg["email_verification_token"]})
    assert v.status_code == 200 and v.json()["status"] == "verified"


def test_duplicate_registration_rejected(client):
    register_and_login(client)
    dup = client.post("/api/v1/auth/register", json={
        "email": "thandi@example.com", "password": "Password123!",
        "first_name": "Thandi", "last_name": "M",
    })
    assert dup.status_code == 409


def test_login_wrong_password(client):
    register_and_login(client)
    r = client.post("/api/v1/auth/login", json={"email": "thandi@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code in (401, 403)
    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401


def test_refresh_token_flow(client):
    _, tokens = register_and_login(client)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200 and r.json()["access_token"]
    # a refresh token cannot be used as an access token
    bad = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert bad.status_code == 401


def test_short_password_rejected(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "x@example.com", "password": "short", "first_name": "X", "last_name": "Y",
    })
    assert r.status_code == 422
