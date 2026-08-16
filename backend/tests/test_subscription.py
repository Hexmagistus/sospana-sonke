"""Tests for subscription state machine, access gating, checkout, and webhooks."""
import json
from datetime import datetime, timedelta, timezone

from tests.conftest import register_and_login
from app.core import security
from app.models.user import User
from app.models.subscription import Subscription, Payment
from app.payments.mock import MockProvider
from app.payments.paystack import PaystackProvider
from app.services.subscription_service import (
    get_or_create_subscription, has_active_access, apply_charge_success, handle_webhook,
)


def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


# ---- route-level ------------------------------------------------------------

def test_default_subscription_is_trial(client):
    _, tokens = register_and_login(client)
    r = client.get("/api/v1/subscription", headers=_auth(tokens))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "TRIAL" and body["has_access"] is True and body["amount_zar"] == 100


def test_checkout_returns_url(client):
    _, tokens = register_and_login(client)
    r = client.post("/api/v1/subscription/checkout", headers=_auth(tokens))
    assert r.status_code == 200
    assert r.json()["reference"] in r.json()["authorization_url"]


def test_mock_pay_activates(client):
    _, tokens = register_and_login(client)
    r = client.post("/api/v1/subscription/mock-pay", headers=_auth(tokens))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ACTIVE" and body["has_access"] is True
    assert body["current_period_end"] is not None


def test_gating_blocks_when_inactive(client, db_engine):
    _, tokens = register_and_login(client)
    # Force the subscription to EXPIRED.
    client.get("/api/v1/subscription", headers=_auth(tokens))  # ensure it exists
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine); s = S()
    try:
        sub = s.query(Subscription).first()
        sub.status = "EXPIRED"; sub.trial_end = None; s.commit()
    finally:
        s.close()
    r = client.post("/api/v1/matches/run", headers=_auth(tokens))
    assert r.status_code == 402


def test_gating_allows_after_payment(client, db_engine):
    _, tokens = register_and_login(client)
    client.get("/api/v1/subscription", headers=_auth(tokens))
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine); s = S()
    try:
        sub = s.query(Subscription).first()
        sub.status = "EXPIRED"; sub.trial_end = None; s.commit()
    finally:
        s.close()
    assert client.post("/api/v1/matches/run", headers=_auth(tokens)).status_code == 402
    client.post("/api/v1/subscription/mock-pay", headers=_auth(tokens))
    assert client.post("/api/v1/matches/run", headers=_auth(tokens)).status_code == 200


def test_cancel_sets_flag(client):
    _, tokens = register_and_login(client)
    client.post("/api/v1/subscription/mock-pay", headers=_auth(tokens))
    r = client.post("/api/v1/subscription/cancel", headers=_auth(tokens))
    assert r.status_code == 200 and r.json()["cancel_at_period_end"] is True


# ---- service-level ----------------------------------------------------------

def _make_user(db, email="u@x.co"):
    u = User(email=email, password_hash=security.hash_password("Password123!"),
             first_name="U", last_name="X", role="candidate", email_verified=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_payment_idempotency(db):
    user = _make_user(db)
    sub = get_or_create_subscription(db, user.id)
    apply_charge_success(db, sub, "REF-1", 40, {"a": 1}, "mock")
    end1 = sub.current_period_end
    # Replaying the same reference must not add a second payment or extend again.
    apply_charge_success(db, sub, "REF-1", 40, {"a": 1}, "mock")
    assert db.query(Payment).count() == 1
    assert sub.current_period_end == end1


def test_access_helper():
    now = datetime.now(timezone.utc)
    active = Subscription(user_id="x", status="ACTIVE", current_period_end=now + timedelta(days=5))
    assert has_active_access(active)
    expired = Subscription(user_id="x", status="ACTIVE", current_period_end=now - timedelta(days=1))
    assert not has_active_access(expired)
    cancelled = Subscription(user_id="x", status="CANCELLED")
    assert not has_active_access(cancelled)


def test_webhook_charge_success(db):
    user = _make_user(db, email="hook@x.co")
    get_or_create_subscription(db, user.id)
    body = json.dumps({"type": "charge_success", "email": "hook@x.co",
                       "reference": "WH-1", "amount_zar": 40}).encode()
    sig = MockProvider.sign(body)
    result = handle_webhook(db, body, sig)
    assert result["handled"] is True
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    assert sub.status == "ACTIVE"


def test_webhook_rejects_bad_signature(db):
    _make_user(db, email="bad@x.co")
    body = json.dumps({"type": "charge_success", "email": "bad@x.co"}).encode()
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        handle_webhook(db, body, "not-a-valid-signature")
    assert exc.value.status_code == 400


def test_paystack_signature_verification(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.PAYSTACK_SECRET_KEY", "sk_test_123", raising=False)
    provider = PaystackProvider()
    import hmac, hashlib
    body = b'{"event":"charge.success","data":{}}'
    good = hmac.new(b"sk_test_123", body, hashlib.sha512).hexdigest()
    assert provider.verify_webhook(body, good) is True
    assert provider.verify_webhook(body, "wrong") is False
