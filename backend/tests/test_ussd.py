"""USSD and WhatsApp stay off, and a live menu never invents a shortcode."""
import hashlib
import hmac
import json

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.sms_alert import SmsAlert
from app.services.channel_menu import contains_shortcode
from tests.test_public_employers import _add_company, _add_role


def _off():
    settings.USSD_ENABLED = False
    settings.USSD_CALLBACK_SECRET = None
    settings.WHATSAPP_VERIFY_TOKEN = None
    settings.WHATSAPP_TOKEN = None
    settings.WHATSAPP_PHONE_NUMBER_ID = None
    settings.WHATSAPP_APP_SECRET = None


def test_ussd_is_off_and_names_no_shortcode(client):
    _off()
    response = client.post("/api/v1/ussd", data={"text": ""})
    assert response.status_code == 404
    assert "No shortcode is configured" in response.text
    assert contains_shortcode(response.text) is False


def test_ussd_menu_lists_a_stored_learnership_and_saves_a_number(client, db_engine):
    settings.USSD_ENABLED = True
    settings.USSD_CALLBACK_SECRET = "test-secret"
    session = sessionmaker(bind=db_engine)()
    try:
        company = _add_company(session, "College")
        _add_role(
            session, company, "Plumbing Learnership",
            opportunity_type="learnership", country="South Africa", province="Gauteng",
        )
        _add_role(
            session, company, "Cape Bursary",
            opportunity_type="bursary", country="South Africa", province="Western Cape",
        )
    finally:
        session.close()

    headers = {"X-Ussd-Secret": "test-secret"}
    denied = client.post("/api/v1/ussd", data={"text": ""}, headers={"X-Ussd-Secret": "nope"})
    assert denied.status_code == 401

    menu = client.post("/api/v1/ussd", data={"text": ""}, headers=headers)
    assert menu.status_code == 200
    assert menu.text.startswith("CON ")
    assert "Categories" in menu.text
    assert len(menu.text.strip()) <= 182
    assert contains_shortcode(menu.text) is False

    listed = client.post("/api/v1/ussd", data={"text": "3"}, headers=headers)
    assert "Plumbing Learnership" in listed.text
    assert listed.text.startswith("END ")
    assert "Cape Bursary" not in listed.text

    province = client.post("/api/v1/ussd", data={"text": "2*9"}, headers=headers)
    assert "Cape Bursary" in province.text
    assert "Plumbing Learnership" not in province.text

    saved = client.post(
        "/api/v1/ussd",
        data={"text": "5*1", "phoneNumber": "+27821234567"},
        headers=headers,
    )
    assert saved.text.startswith("END Saved")
    assert "No SMS was sent" in saved.text
    assert contains_shortcode(saved.text) is False
    check = sessionmaker(bind=db_engine)()
    try:
        row = check.query(SmsAlert).one()
        assert row.phone == "+27821234567"
        assert row.active is True
    finally:
        check.close()
    _off()


def test_whatsapp_is_off_until_every_value_is_set(client, monkeypatch):
    _off()
    calls = []
    monkeypatch.setattr("app.api.routes_channels.deliver_whatsapp", lambda to, body: calls.append((to, body)) or True)
    off = client.post("/api/v1/whatsapp", json={"entry": []})
    assert off.status_code == 404
    assert calls == []
    assert "No phone number is configured" in off.text

    settings.WHATSAPP_VERIFY_TOKEN = "verify"
    settings.WHATSAPP_TOKEN = "token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "123"
    settings.WHATSAPP_APP_SECRET = "app-secret"
    challenge = client.get("/api/v1/whatsapp", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "verify",
        "hub.challenge": "99",
    })
    assert challenge.status_code == 200
    assert challenge.text == "99"

    payload = {"entry": [{"changes": [{"value": {"messages": [{
        "from": "27821234567",
        "type": "text",
        "text": {"body": ""},
    }]}}]}]}
    raw = json.dumps(payload).encode()
    digest = hmac.new(b"app-secret", raw, hashlib.sha256).hexdigest()
    sent = client.post(
        "/api/v1/whatsapp",
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": f"sha256={digest}"},
    )
    assert sent.status_code == 200
    assert calls and calls[0][0] == "27821234567"
    assert "Categories" in calls[0][1]
    assert contains_shortcode(calls[0][1]) is False
    _off()
