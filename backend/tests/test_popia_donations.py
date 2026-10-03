"""POPIA opt-in, admin tags, public counts, and cash-send donations."""
import logging

from app.core.config import settings
from app.core.logging import RedactEmailFilter
from app.models.admin_ops import AdminAuditLog
from tests.conftest import make_admin, register_and_login


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_register_opportunity_alerts_default_off(client):
    reg, _ = register_and_login(client, email="off@example.com")
    assert reg["user"]["notify_opportunity_alerts"] is False


def test_register_can_opt_in_separately(client):
    reg, tokens = register_and_login(
        client, email="on@example.com",
        preferred_position="Welder", notify_opportunity_alerts=True, accepted_policy=True,
    )
    assert reg["user"]["notify_opportunity_alerts"] is True
    me = client.get("/api/v1/auth/me", headers=_auth(tokens))
    assert me.status_code == 200
    assert me.json()["notify_opportunity_alerts"] is True


def test_export_includes_alert_flag_and_hides_nothing_personal_from_the_owner(client):
    _, tokens = register_and_login(client, email="export@example.com", notify_opportunity_alerts=True)
    exported = client.get("/api/v1/account/export", headers=_auth(tokens))
    assert exported.status_code == 200
    body = exported.json()
    assert body["account"]["notify_opportunity_alerts"] is True
    assert body["account"]["email"] == "export@example.com"
    assert "profile" in body


def test_owner_can_switch_alerts_off(client):
    _, tokens = register_and_login(client, email="switch@example.com", notify_opportunity_alerts=True)
    off = client.put("/api/v1/account/opportunity-alerts", headers=_auth(tokens), json={"enabled": False})
    assert off.status_code == 200
    assert off.json()["notify_opportunity_alerts"] is False


def test_compliance_contact_is_public(client):
    r = client.get("/api/v1/compliance")
    assert r.status_code == 200
    body = r.json()
    assert body["information_officer_name"]
    assert "@" in body["information_officer_email"]


def test_log_filter_redacts_email_addresses():
    filt = RedactEmailFilter()
    record = logging.LogRecord("t", logging.ERROR, "", 0, "Failed for %s", ("person@example.com",), None)
    assert filt.filter(record) is True
    assert "person@example.com" not in record.getMessage()
    assert "[redacted-email]" in record.getMessage()


def test_admin_tag_is_available_without_an_email_choice_and_is_audited(client, db_engine):
    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    quiet, quiet_tokens = register_and_login(client, email="notags@example.com", preferred_position="Chef")
    tagged = client.post(
        f"/api/v1/admin/users/{quiet['user']['id']}/tags",
        headers=_auth(admin),
        json={"tag": "hospitality", "link_url": "https://acme.example/careers"},
    )
    assert tagged.status_code == 200, tagged.text
    assert "hospitality" in tagged.json()["tags"]
    assert tagged.json()["notice_sent"] == 1
    assert tagged.json()["notice_emailed"] == 0
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(quiet_tokens)).json()
             if n["type"] == "admin_suggestion"]
    assert len(notes) == 1
    assert notes[0]["email_sent"] is False

    opted, _ = register_and_login(
        client, email="tags@example.com",
        preferred_position="Chef", notify_opportunity_alerts=True, tagging_email=True,
    )
    ok = client.post(
        f"/api/v1/admin/users/{opted['user']['id']}/tags",
        headers=_auth(admin), json={"tag": "hospitality"},
    )
    assert ok.status_code == 200, ok.text
    assert "hospitality" in ok.json()["tags"]

    listed = client.get("/api/v1/admin/users?with_preference=true", headers=_auth(admin))
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert opted["user"]["id"] in ids
    row = next(r for r in listed.json() if r["id"] == opted["user"]["id"])
    assert row["notify_opportunity_alerts"] is True
    assert row["tagging_email"] is True
    assert "hospitality" in row["tags"]

    from sqlalchemy.orm import sessionmaker
    db = sessionmaker(bind=db_engine)()
    try:
        audits = db.query(AdminAuditLog).filter(AdminAuditLog.action == "tag").all()
        assert audits
        assert all("@" not in (a.detail or "") for a in audits)
    finally:
        db.close()


def test_directory_stats_are_public_counts(client, db):
    from app.models.company import Company
    db.add(Company(company_name="Stats SA One", country="South Africa", active=True))
    db.add(Company(company_name="Stats SA Two", country="South Africa", active=False))
    db.add(Company(company_name="Stats Zim", country="Zimbabwe", active=True))
    db.commit()
    r = client.get("/api/v1/companies/stats")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["employers"], int)
    assert body["employers"] >= 3
    assert body["by_country"]["South Africa"] == 2
    assert body["by_country"]["Zimbabwe"] == 1
    assert body["countries"] >= 2


def test_cashsend_is_hidden_until_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "DONATION_CASHSEND_NUMBER", None)
    hidden = client.get("/api/v1/donations/cashsend")
    assert hidden.status_code == 200
    assert hidden.json()["ready"] is False
    assert hidden.json()["number"] is None

    monkeypatch.setattr(settings, "DONATION_CASHSEND_NUMBER", "+27 82 000 0000")
    shown = client.get("/api/v1/donations/cashsend")
    assert shown.json()["ready"] is True
    assert shown.json()["number"] == "+27820000000"
    assert shown.json()["reference"] == "Sospana Sonke donation"

    monkeypatch.setattr(settings, "DONATION_CASHSEND_NUMBER", "not-a-number")
    bad = client.get("/api/v1/donations/cashsend")
    assert bad.json()["ready"] is False
