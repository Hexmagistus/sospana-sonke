"""Tests for the one-off donation checkout + webhook flow."""
import json

from app.models.donation import Donation
from app.payments.mock import MockProvider
from app.services.subscription_service import handle_webhook


def test_donation_checkout_returns_url(client):
    r = client.post("/api/v1/donations/checkout", json={
        "amount_zar": 50, "email": "donor@example.com", "name": "Anon Donor",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["reference"].startswith("DON-")
    assert body["reference"] in body["authorization_url"]


def test_donation_checkout_no_login_required(client):
    # No Authorization header at all -- donations must work for anonymous visitors.
    r = client.post("/api/v1/donations/checkout", json={
        "amount_zar": 20, "email": "anon@example.com",
    })
    assert r.status_code == 200


def test_donation_checkout_rejects_amount_out_of_range(client):
    r = client.post("/api/v1/donations/checkout", json={
        "amount_zar": 999999, "email": "donor@example.com",
    })
    assert r.status_code == 400


def test_donation_checkout_rejects_bad_email(client):
    r = client.post("/api/v1/donations/checkout", json={
        "amount_zar": 20, "email": "not-an-email",
    })
    assert r.status_code == 422


def test_donation_webhook_charge_success_is_routed_and_idempotent(db):
    donation = Donation(
        donor_name="Test Donor", donor_email="hook@x.co", amount_zar=100,
        currency="ZAR", provider="mock", provider_reference="DON-abc123", status="pending",
    )
    db.add(donation)
    db.commit()

    body = json.dumps({"type": "charge_success", "email": "hook@x.co",
                       "reference": "DON-abc123", "amount_zar": 100}).encode()
    sig = MockProvider.sign(body)
    result = handle_webhook(db, body, sig)
    assert result["handled"] is True
    assert result["type"] == "donation_success"

    db.refresh(donation)
    assert donation.status == "success"

    # Replaying the same webhook must not error or change anything.
    result2 = handle_webhook(db, body, sig)
    assert result2["handled"] is True
    db.refresh(donation)
    assert donation.status == "success"


def test_donation_webhook_unknown_reference_is_ignored_gracefully(db):
    body = json.dumps({"type": "charge_success", "email": "nobody@x.co",
                       "reference": "DON-does-not-exist", "amount_zar": 20}).encode()
    sig = MockProvider.sign(body)
    result = handle_webhook(db, body, sig)
    assert result["handled"] is False
