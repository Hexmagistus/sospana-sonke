"""Google sign-in must not preserve a pre-registered account, and admins need MFA."""
import pyotp
from sqlalchemy.orm import sessionmaker

from app.core import security
from app.core.config import settings
from app.models.user import User
from tests.conftest import register_and_login


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _stub_google(monkeypatch, email):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")

    class Resp:
        status_code = 200

        def json(self):
            return {
                "aud": settings.GOOGLE_CLIENT_ID,
                "iss": "accounts.google.com",
                "email": email,
                "email_verified": "true",
                "given_name": "Ada",
                "family_name": "Lovelace",
            }

    monkeypatch.setattr("app.api.routes_auth.httpx.get", lambda *args, **kwargs: Resp())


def test_google_reclaims_an_unverified_preregistration(client, monkeypatch):
    email = "owner@example.com"
    reg = client.post("/api/v1/auth/register", json={
        "email": email, "password": "SquatterPass1!",
        "first_name": "Not", "last_name": "Owner",
    })
    assert reg.status_code == 201
    assert reg.json()["user"]["email_verified"] is False
    squatter = client.post("/api/v1/auth/login", json={"email": email, "password": "SquatterPass1!"})
    assert squatter.status_code == 200
    old_token = squatter.json()["access_token"]

    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(squatter.json()))
    secret = setup.json()["secret"]
    enabled = client.post("/api/v1/auth/mfa/enable", headers=_auth(squatter.json()),
                          json={"code": pyotp.TOTP(secret).now()})
    assert enabled.status_code == 200

    blocked = client.get("/api/v1/profile", headers=_auth(squatter.json()))
    assert blocked.status_code == 403
    assert "Verify your email" in blocked.json()["detail"]
    assert client.get("/api/v1/auth/me", headers=_auth(squatter.json())).status_code == 200

    _stub_google(monkeypatch, email)
    signed = client.post("/api/v1/auth/google", json={"credential": "fake-id-token"})
    assert signed.status_code == 200, signed.text
    me = client.get("/api/v1/auth/me", headers=_auth(signed.json()))
    assert me.status_code == 200
    assert me.json()["email_verified"] is True
    assert me.json()["mfa_enabled"] is False
    assert client.post("/api/v1/auth/login",
                       json={"email": email, "password": "SquatterPass1!"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


def test_google_requires_mfa_when_the_verified_account_has_it(client, monkeypatch):
    email = "mfa-owner@example.com"
    _, tokens = register_and_login(client, email=email, password="Password123!")
    setup = client.post("/api/v1/auth/mfa/setup", headers=_auth(tokens))
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    assert client.post("/api/v1/auth/mfa/enable", headers=_auth(tokens), json={"code": code}).status_code == 200

    _stub_google(monkeypatch, email)
    missing = client.post("/api/v1/auth/google", json={"credential": "fake-id-token"})
    assert missing.status_code == 401
    assert "MFA" in missing.json()["detail"]
    ok = client.post("/api/v1/auth/google", json={"credential": "fake-id-token", "otp_code": code})
    assert ok.status_code == 200, ok.text
    assert client.post("/api/v1/auth/login",
                       json={"email": email, "password": "Password123!", "otp_code": code}).status_code == 200


def test_google_links_a_verified_account_without_mfa(client, monkeypatch):
    email = "plain@example.com"
    register_and_login(client, email=email, password="Password123!")
    _stub_google(monkeypatch, email)
    signed = client.post("/api/v1/auth/google", json={"credential": "fake-id-token"})
    assert signed.status_code == 200, signed.text
    assert client.post("/api/v1/auth/login",
                       json={"email": email, "password": "Password123!"}).status_code == 200


def test_admin_tools_stay_closed_until_mfa_is_on_and_cannot_be_turned_off(client, db_engine):
    email, password = "boot-admin@example.com", "AdminPass123!"
    S = sessionmaker(bind=db_engine)
    db = S()
    try:
        db.add(User(email=email, password_hash=security.hash_password(password),
                    first_name="Admin", last_name="User", role="admin", email_verified=True))
        db.commit()
    finally:
        db.close()

    signed = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert signed.status_code == 200, signed.text
    headers = _auth(signed.json())
    blocked = client.get("/api/v1/admin/dashboard", headers=headers)
    assert blocked.status_code == 403
    assert "two-factor" in blocked.json()["detail"].lower()

    setup = client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup.status_code == 200, setup.text
    code = pyotp.TOTP(setup.json()["secret"]).now()
    enabled = client.post("/api/v1/auth/mfa/enable", headers=headers, json={"code": code})
    assert enabled.status_code == 200 and enabled.json()["mfa_enabled"] is True
    assert client.get("/api/v1/admin/dashboard", headers=headers).status_code == 200

    again = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert again.status_code == 401
    with_code = client.post("/api/v1/auth/login",
                            json={"email": email, "password": password, "otp_code": code})
    assert with_code.status_code == 200
    refused = client.post("/api/v1/auth/mfa/disable", headers=_auth(with_code.json()), json={"code": code})
    assert refused.status_code == 403
