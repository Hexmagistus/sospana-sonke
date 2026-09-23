"""Security controls added in the 2026-09-24 hardening pass.

Covers: real client IP behind the proxy, per-account lockout, login timing /
enumeration, session revocation (token_version), single-use reset links, the
mock payment provider being inert in production, and per-user rate-limit keys.
"""
import json
from types import SimpleNamespace

import pytest

from app.core import security
from app.core.client_ip import client_ip
from app.core.config import settings
from app.core.rate_limit import user_or_ip_key
from tests.conftest import register_and_login

PW = "Password123!"
EMAIL = "thandi@example.com"


def _req(xff=None, host="10.0.0.5", auth=None):
    headers = {}
    if xff is not None:
        headers["x-forwarded-for"] = xff
    if auth:
        headers["authorization"] = auth
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host))


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---- client IP ----------------------------------------------------------------

def test_client_ip_uses_proxy_appended_entry_not_spoofable_first(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    assert client_ip(_req("1.2.3.4, 41.13.2.9")) == "41.13.2.9"
    assert client_ip(_req("41.13.2.9")) == "41.13.2.9"


def test_client_ip_falls_back_to_socket(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    assert client_ip(_req(None)) == "10.0.0.5"
    assert client_ip(_req("not-an-ip")) == "10.0.0.5"
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 0)
    assert client_ip(_req("41.13.2.9")) == "10.0.0.5"


def test_rate_limit_key_is_per_user_for_valid_token_else_ip(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    tok = security.create_access_token("user-123", "candidate")
    assert user_or_ip_key(_req("9.9.9.9", auth=f"Bearer {tok}")) == "user:user-123"
    assert user_or_ip_key(_req("9.9.9.9", auth="Bearer forged.token.value")) == "ip:9.9.9.9"
    assert user_or_ip_key(_req("9.9.9.9")) == "ip:9.9.9.9"


# ---- login: enumeration + lockout -----------------------------------------------

def test_unknown_email_and_wrong_password_look_identical(client):
    register_and_login(client)
    a = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": PW})
    b = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "Wrong-pass-1"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_account_locks_after_repeated_failures_even_for_correct_password(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILURES", 3)
    register_and_login(client)
    for _ in range(3):
        assert client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "Wrong-pass-1"}).status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PW})
    assert r.status_code == 429


def test_successful_login_resets_failure_counter(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_MAX_FAILURES", 3)
    register_and_login(client)
    for _ in range(2):
        client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "Wrong-pass-1"})
    assert client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PW}).status_code == 200
    for _ in range(2):
        client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "Wrong-pass-1"})
    assert client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PW}).status_code == 200


# ---- session revocation -------------------------------------------------------

def test_logout_all_revokes_access_and_refresh_tokens(client):
    _, tokens = register_and_login(client)
    assert client.get("/api/v1/auth/me", headers=_auth(tokens)).status_code == 200
    assert client.post("/api/v1/auth/logout-all", headers=_auth(tokens)).status_code == 200
    assert client.get("/api/v1/auth/me", headers=_auth(tokens)).status_code == 401
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401
    # A fresh sign-in works normally afterwards.
    fresh = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PW}).json()
    assert client.get("/api/v1/auth/me", headers=_auth(fresh)).status_code == 200


def test_pre_versioning_tokens_still_valid(client):
    """Tokens minted before this change carry no 'tv' claim; deploying must not log everyone out."""
    reg, _ = register_and_login(client)
    legacy = security._create_token(reg["user"]["id"], "access",
                                    __import__("datetime").timedelta(minutes=5), {"role": "candidate"})
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 200


def test_reset_link_is_single_use_and_signs_out_everywhere(client):
    _, tokens = register_and_login(client)
    reset = client.post("/api/v1/auth/password-reset/request", json={"email": EMAIL}).json()["reset_token"]
    ok = client.post("/api/v1/auth/password-reset/confirm", json={"token": reset, "new_password": "BrandNew123!"})
    assert ok.status_code == 200
    again = client.post("/api/v1/auth/password-reset/confirm", json={"token": reset, "new_password": "Another123!"})
    assert again.status_code == 400
    assert client.get("/api/v1/auth/me", headers=_auth(tokens)).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "BrandNew123!"}).status_code == 200


# ---- payments -----------------------------------------------------------------

def test_mock_webhooks_rejected_in_production(client, monkeypatch):
    from app.payments.mock import MockProvider
    body = json.dumps({"event": "charge.success", "data": {"reference": "DON-abc", "amount": 10000}}).encode()
    sig = MockProvider.sign(body)
    assert MockProvider().verify_webhook(body, sig) is True
    monkeypatch.setattr(settings, "ENV", "production")
    assert MockProvider().verify_webhook(body, sig) is False
    r = client.post("/api/v1/subscription/webhook", content=body, headers={"x-signature": sig})
    assert r.status_code == 400


def test_card_donations_disabled_in_production_without_real_provider(client, monkeypatch):
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    r = client.post("/api/v1/donations/checkout", json={"amount_zar": 50, "email": "d@example.com"})
    assert r.status_code == 503


# ---- DAST follow-ups (2026-09-24 ZAP scan) ------------------------------------

def test_cron_secret_only_accepted_in_header(client, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "s3cret-value")
    assert client.post("/api/v1/cron/run/nope?token=s3cret-value").status_code == 401
    assert client.post("/api/v1/cron/run/nope", headers={"X-Cron-Secret": "s3cret-value"}).status_code == 404


def test_documents_survive_control_characters():
    from app.documents.render import render_cv_docx, render_letter_docx
    nasty = "Water\x00 treatment\x0b operator\x1f"
    cv = {"full_name": nasty, "summary": nasty, "skills": [nasty], "experience": [
        {"job_title": nasty, "company": nasty, "responsibilities": nasty}]}
    assert render_cv_docx(cv)[:2] == b"PK"
    assert render_letter_docx("Dear hiring manager,\x00\x07\n\nI apply.")[:2] == b"PK"


def test_smtp_user_also_read_from_production_typo(monkeypatch):
    """Render had SMPT_USER (typo); email silently stopped. Both spellings must work."""
    from app.core.config import Settings
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.setenv("SMPT_USER", "sender@gmail.com")
    assert Settings().SMTP_USER == "sender@gmail.com"
    monkeypatch.setenv("SMTP_USER", "correct@gmail.com")
    assert Settings().SMTP_USER == "correct@gmail.com"
