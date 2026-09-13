"""Tests for the (now purely historical) subscription ledger and webhook.

Sospana Sonke is free forever: subscriptions were permanently removed as a
gate on every route, and checkout/cancel/mock-pay were removed outright (see
app/api/routes_subscription.py and app/services/subscription_service.py).
What's left to test: access is unconditional regardless of subscription
status, the removed endpoints are gone for good, and the payment
ledger/webhook -- which donations still route through -- still works
correctly.
"""
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


def test_checkout_cancel_and_mock_pay_are_permanently_removed(client):
    _, tokens = register_and_login(client)
    for path in ("/api/v1/subscription/checkout", "/api/v1/subscription/cancel",
                "/api/v1/subscription/mock-pay"):
        r = client.post(path, headers=_auth(tokens))
        assert r.status_code == 410, path


def test_access_always_granted_regardless_of_subscription_status(client, db_engine):
    """The core "free forever" guarantee: even a fully expired/cancelled
    subscription never blocks a feature that used to require an active one."""
    _, tokens = register_and_login(client)
    client.get("/api/v1/subscription", headers=_auth(tokens))  # ensure it exists
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine); s = S()
    try:
        sub = s.query(Subscription).first()
        sub.status = "EXPIRED"; sub.trial_end = None; s.commit()
    finally:
        s.close()
    # /matches/run used to 402 here; it no longer gates on subscription at all.
    assert client.post("/api/v1/matches/run", headers=_auth(tokens)).status_code == 200


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


def test_access_helper_is_unconditionally_true():
    """has_active_access() always returns True now, whatever the subscription
    status -- Sospana Sonke is free forever for every account."""
    now = datetime.now(timezone.utc)
    active = Subscription(user_id="x", status="ACTIVE", current_period_end=now + timedelta(days=5))
    expired = Subscription(user_id="x", status="ACTIVE", current_period_end=now - timedelta(days=1))
    cancelled = Subscription(user_id="x", status="CANCELLED")
    never_paid = Subscription(user_id="x", status="EXPIRED")
    for sub in (active, expired, cancelled, never_paid):
        assert has_active_access(sub) is True


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
