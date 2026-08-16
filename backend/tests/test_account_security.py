"""Tests for MFA (TOTP) enrolment + MFA-gated login, and password reset."""
import pyotp

from tests.conftest import register_and_login


def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_mfa_enrol_login_and_disable(client):
    _, tokens = register_and_login(client, email="mfa@example.com", password="Password123!")
    h = _auth(tokens)

    setup = client.post("/api/v1/auth/mfa/setup", headers=h)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert "otpauth://" in setup.json()["otpauth_uri"]
    totp = pyotp.TOTP(secret)

    # wrong code rejected
    assert client.post("/api/v1/auth/mfa/enable", headers=h, json={"code": "000000"}).status_code == 400
    # correct code enables
    en = client.post("/api/v1/auth/mfa/enable", headers=h, json={"code": totp.now()})
    assert en.status_code == 200 and en.json()["mfa_enabled"] is True

    # login now requires OTP
    no_otp = client.post("/api/v1/auth/login", json={"email": "mfa@example.com", "password": "Password123!"})
    assert no_otp.status_code == 401
    with_otp = client.post("/api/v1/auth/login",
                           json={"email": "mfa@example.com", "password": "Password123!", "otp_code": totp.now()})
    assert with_otp.status_code == 200 and with_otp.json()["access_token"]

    # disable with a valid code -> login no longer needs OTP
    dis = client.post("/api/v1/auth/mfa/disable", headers=h, json={"code": totp.now()})
    assert dis.status_code == 200 and dis.json()["mfa_enabled"] is False
    assert client.post("/api/v1/auth/login",
                       json={"email": "mfa@example.com", "password": "Password123!"}).status_code == 200


def test_password_reset_flow(client):
    register_and_login(client, email="reset@example.com", password="OldPassword1!")

    req = client.post("/api/v1/auth/password-reset/request", json={"email": "reset@example.com"})
    assert req.status_code == 200
    token = req.json()["reset_token"]
    assert token  # returned in non-production for testing

    # confirm with new password
    conf = client.post("/api/v1/auth/password-reset/confirm",
                       json={"token": token, "new_password": "BrandNew1!"})
    assert conf.status_code == 200

    # old password fails, new password works
    assert client.post("/api/v1/auth/login",
                       json={"email": "reset@example.com", "password": "OldPassword1!"}).status_code == 401
    assert client.post("/api/v1/auth/login",
                       json={"email": "reset@example.com", "password": "BrandNew1!"}).status_code == 200


def test_password_reset_request_no_enumeration(client):
    # Unknown email still returns 200 (no account enumeration) with no token.
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and r.json()["reset_token"] is None


def test_password_reset_bad_token(client):
    r = client.post("/api/v1/auth/password-reset/confirm",
                    json={"token": "not-a-token", "new_password": "Whatever1!"})
    assert r.status_code == 400


def test_password_reset_short_password_rejected(client):
    register_and_login(client, email="short@example.com", password="OldPassword1!")
    token = client.post("/api/v1/auth/password-reset/request",
                        json={"email": "short@example.com"}).json()["reset_token"]
    r = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "short"})
    assert r.status_code == 422
