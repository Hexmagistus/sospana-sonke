"""Brevo HTTPS mail, with the SMTP path left in place when the key is unset."""
import logging

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models.user import User
from app.notifications.email import (
    BREVO_TIMEOUT_SECONDS,
    BREVO_URL,
    BrevoEmailProvider,
    ConsoleEmailProvider,
    SMTPEmailProvider,
    get_email_provider,
    reset_brevo_send_state,
)
from app.notifications.login_alert import send_login_alert
from app.services.notification_service import create_notification, notify_admin_suggestion


@pytest.fixture(autouse=True)
def _clean_brevo(monkeypatch):
    reset_brevo_send_state()
    monkeypatch.setattr(settings, "BREVO_API_KEY", None)
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", None)
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "Sospana Sonke")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Sospana Sonke <news@sospanasonke.co.za>")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "console")
    yield
    reset_brevo_send_state()


def _enable_brevo(monkeypatch, key="test-brevo-key", sender="news@sospanasonke.co.za"):
    monkeypatch.setattr(settings, "BREVO_API_KEY", key)
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", sender)
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "smtp")


def _capture_posts(monkeypatch, responses):
    calls = []

    def _post(url, *, headers, payload, timeout):
        calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        status, text = responses[min(len(calls) - 1, len(responses) - 1)]
        return httpx.Response(status, text=text)

    monkeypatch.setattr("app.notifications.email._post_brevo", _post)
    return calls


def test_key_selects_brevo_even_when_smtp_is_configured(monkeypatch):
    _enable_brevo(monkeypatch)
    assert isinstance(get_email_provider(), BrevoEmailProvider)


def test_unset_key_keeps_smtp_and_console(monkeypatch):
    assert isinstance(get_email_provider(), ConsoleEmailProvider)
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "smtp")
    assert isinstance(get_email_provider(), SMTPEmailProvider)


def test_brevo_posts_the_transactional_payload(monkeypatch):
    _enable_brevo(monkeypatch)
    monkeypatch.setattr(settings, "EMAIL_FROM", "Desk <hello@sospanasonke.co.za>")
    calls = _capture_posts(monkeypatch, [(201, "{}")])
    sent = get_email_provider().send(
        "person@example.com",
        "Reset your password",
        "Line one\n<script>alert(1)</script>",
    )
    assert sent is True
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == BREVO_URL
    assert call["timeout"] == BREVO_TIMEOUT_SECONDS == 10.0
    assert call["headers"]["api-key"] == "test-brevo-key"
    assert call["payload"]["sender"] == {"name": "Sospana Sonke", "email": "news@sospanasonke.co.za"}
    assert call["payload"]["to"] == [{"email": "person@example.com"}]
    assert call["payload"]["subject"] == "Reset your password"
    assert call["payload"]["textContent"] == "Line one\n<script>alert(1)</script>"
    assert "&lt;script&gt;" in call["payload"]["htmlContent"]
    assert "<script>" not in call["payload"]["htmlContent"]
    assert call["payload"]["replyTo"] == {"email": "hello@sospanasonke.co.za", "name": "Desk"}


def test_reply_to_omitted_when_it_matches_the_sender(monkeypatch):
    _enable_brevo(monkeypatch, sender="news@sospanasonke.co.za")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Sospana Sonke <news@sospanasonke.co.za>")
    calls = _capture_posts(monkeypatch, [(201, "{}")])
    assert get_email_provider().send("a@example.com", "Hi", "Body") is True
    assert "replyTo" not in calls[0]["payload"]


def test_custom_sender_name(monkeypatch):
    _enable_brevo(monkeypatch)
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "Sonke Desk")
    calls = _capture_posts(monkeypatch, [(201, "{}")])
    get_email_provider().send("a@example.com", "Hi", "Body")
    assert calls[0]["payload"]["sender"]["name"] == "Sonke Desk"


def test_missing_sender_does_not_call_brevo_and_logs_once(monkeypatch, caplog):
    monkeypatch.setattr(settings, "BREVO_API_KEY", "test-brevo-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "  ")
    calls = _capture_posts(monkeypatch, [(201, "{}")])
    with caplog.at_level(logging.WARNING):
        assert get_email_provider().send("person@example.com", "Secret subject", "Secret body") is False
        assert get_email_provider().send("person@example.com", "Secret subject", "Secret body") is False
    assert calls == []
    assert caplog.text.count("missing_sender") == 1
    assert "test-brevo-key" not in caplog.text
    assert "person@example.com" not in caplog.text
    assert "Secret body" not in caplog.text


@pytest.mark.parametrize("status,text,reason", [
    (401, "unauthorized", "auth"),
    (403, "", "auth"),
    (429, "", "quota"),
    (400, '{"message":"You have exceeded your daily quota"}', "quota"),
])
def test_quota_or_auth_stops_and_logs_once(monkeypatch, caplog, status, text, reason):
    _enable_brevo(monkeypatch)
    calls = _capture_posts(monkeypatch, [(status, text), (201, "{}")])
    with caplog.at_level(logging.WARNING):
        assert get_email_provider().send("person@example.com", "Subject", "Body text") is False
        assert get_email_provider().send("other@example.com", "Subject", "Body text") is False
    assert len(calls) == 1
    assert caplog.text.count(reason) == 1
    assert "test-brevo-key" not in caplog.text
    assert "person@example.com" not in caplog.text
    assert "other@example.com" not in caplog.text
    assert "Body text" not in caplog.text
    assert "daily quota" not in caplog.text


def test_other_failures_do_not_stop_the_next_send(monkeypatch, caplog):
    _enable_brevo(monkeypatch)

    def _post(url, *, headers, payload, timeout):
        raise httpx.ConnectError("blocked")

    monkeypatch.setattr("app.notifications.email._post_brevo", _post)
    with caplog.at_level(logging.WARNING):
        assert get_email_provider().send("person@example.com", "Subject", "Body text") is False
    calls = _capture_posts(monkeypatch, [(502, "bad gateway"), (201, "{}")])
    assert get_email_provider().send("person@example.com", "Subject", "Body text") is False
    assert get_email_provider().send("person@example.com", "Subject", "Body text") is True
    assert len(calls) == 2
    assert "test-brevo-key" not in caplog.text
    assert "person@example.com" not in caplog.text
    assert "Body text" not in caplog.text
    assert "ConnectError" in caplog.text


def test_smtp_path_unchanged_when_key_is_unset(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USER", "mailer@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Sospana Sonke <mailer@example.com>")
    seen = []

    class _SMTP:
        def __init__(self, host, port, timeout=None):
            seen.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            seen.append("starttls")

        def login(self, user, password):
            seen.append(("login", user, password))

        def sendmail(self, sender, recipients, message):
            seen.append(("sendmail", sender, recipients))

    monkeypatch.setattr("smtplib.SMTP", _SMTP)

    def _forbid(*args, **kwargs):
        raise AssertionError("Brevo was called")

    monkeypatch.setattr("app.notifications.email._post_brevo", _forbid)
    assert get_email_provider().send("person@example.com", "Hi", "Body") is True
    assert seen[0] == ("connect", "smtp.example.com", 587, 15)
    assert "starttls" in seen
    assert ("login", "mailer@example.com", "app-password") in seen
    assert ("sendmail", "Sospana Sonke <mailer@example.com>", ["person@example.com"]) in seen


def test_console_outbox_when_neither_brevo_nor_smtp():
    ConsoleEmailProvider.outbox.clear()
    assert get_email_provider().send("person@example.com", "Hi", "Body") is True
    assert ConsoleEmailProvider.outbox[-1]["to"] == "person@example.com"


def test_strong_match_and_briefing_use_brevo_after_commit(db, monkeypatch):
    _enable_brevo(monkeypatch)
    monkeypatch.setattr(settings, "NOTIFY_EMAILS", True)
    calls = _capture_posts(monkeypatch, [(201, "{}"), (201, "{}")])
    user = User(
        email="match@example.com",
        password_hash=security.hash_password("Password123!"),
        first_name="Naledi",
        last_name="Dlamini",
        notify_opportunity_alerts=True,
    )
    db.add(user)
    db.commit()
    open_during = []

    real_post = __import__("app.notifications.email", fromlist=["_post_brevo"])._post_brevo

    def _watching(url, *, headers, payload, timeout):
        open_during.append(db.in_transaction())
        return real_post(url, headers=headers, payload=payload, timeout=timeout)

    monkeypatch.setattr("app.notifications.email._post_brevo", _watching)
    note = create_notification(
        db, user_id=user.id, to_email=user.email, type="strong_match",
        title="A match", body="Details", related_id="match-1",
    )
    briefing = create_notification(
        db, user_id=user.id, to_email=user.email, type="daily_agent_briefing",
        title="Your briefing", body="Three roles", related_id="run-1",
    )
    assert note is not None and note.email_sent is True
    assert briefing is not None and briefing.email_sent is True
    assert open_during == [False, False]
    assert [c["payload"]["subject"] for c in calls] == ["A match", "Your briefing"]
    assert not db.in_transaction()


def test_opted_out_admin_suggestion_does_not_email(db, monkeypatch):
    """POPIA: no in-app notice and no email when opportunity alerts are off."""
    _enable_brevo(monkeypatch)
    monkeypatch.setattr(settings, "NOTIFY_EMAILS", True)
    calls = _capture_posts(monkeypatch, [(201, "{}")])
    opted_out = User(
        email="out@example.com",
        password_hash=security.hash_password("Password123!"),
        first_name="Out",
        last_name="User",
        preferred_position="Nurse",
        notify_opportunity_alerts=False,
    )
    db.add(opted_out)
    db.commit()
    sent, duplicates = notify_admin_suggestion(
        db, users=[opted_out], title="A post", body="Look here",
        link_url="https://apply.example.com/nurse",
    )
    assert (sent, duplicates) == (0, 0)
    assert calls == []


def test_email_html_button_rejects_a_javascript_line():
    from app.notifications.email import _html_from_text
    html = _html_from_text("javascript:alert(1)\nhttps://jobs.example/apply")
    assert html.count("<a ") == 1
    assert 'href="https://jobs.example/apply"' in html
    assert 'href="javascript:' not in html.lower()


def test_opted_in_suggestion_emails_the_link_once(db, monkeypatch):
    _enable_brevo(monkeypatch)
    monkeypatch.setattr(settings, "NOTIFY_EMAILS", True)
    calls = _capture_posts(monkeypatch, [(201, "{}"), (201, "{}")])
    user = User(
        email="in@example.com",
        password_hash=security.hash_password("Password123!"),
        first_name="In",
        last_name="User",
        preferred_position="Nurse",
        notify_opportunity_alerts=True,
    )
    db.add(user)
    db.commit()
    sent, duplicates = notify_admin_suggestion(
        db, users=[user], title="Ward clerk",
        body="Please look. <script>alert(1)</script>",
        link_url="https://apply.example.com/nurse",
    )
    assert (sent, duplicates) == (1, 0)
    assert len(calls) == 1
    text = calls[0]["payload"]["textContent"]
    html_body = calls[0]["payload"]["htmlContent"]
    assert "https://apply.example.com/nurse" in text
    assert "Tagged by the Sospana Sonke team." in text
    assert 'href="https://apply.example.com/nurse"' in html_body
    assert "Open this listing" in html_body
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
    again, dup_again = notify_admin_suggestion(
        db, users=[user], title="Ward clerk", body="Please look again.",
        link_url="https://apply.example.com/nurse",
    )
    assert (again, dup_again) == (0, 1)
    assert len(calls) == 1


def test_password_reset_uses_brevo_with_no_open_transaction(client, db_engine, monkeypatch):
    _enable_brevo(monkeypatch)
    calls = _capture_posts(monkeypatch, [(201, "{}"), (201, "{}")])
    reg = client.post("/api/v1/auth/register", json={
        "email": "reset-brevo@example.com",
        "password": "StrongPass123!",
        "first_name": "Thandi",
        "last_name": "Mokoena",
        "accepted_policy": True,
        "notify_opportunity_alerts": False,
    })
    assert reg.status_code == 201, reg.text
    assert calls[0]["payload"]["subject"].startswith("Verify")

    live: list[Session] = []

    def _track(session, transaction, connection):
        if connection.engine is db_engine:
            live.append(session)

    event.listen(Session, "after_begin", _track)
    open_during = []

    def _post(url, *, headers, payload, timeout):
        open_during.append(any(s.in_transaction() for s in live))
        calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        return httpx.Response(201, text="{}")

    monkeypatch.setattr("app.notifications.email._post_brevo", _post)
    try:
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "reset-brevo@example.com"},
        )
    finally:
        event.remove(Session, "after_begin", _track)
    assert response.status_code == 200
    assert response.json()["status"].startswith("If that email exists")
    assert open_during == [False]
    assert calls[-1]["payload"]["subject"].startswith("Reset")
    assert calls[-1]["payload"]["to"] == [{"email": "reset-brevo@example.com"}]


def test_login_alert_uses_the_shared_brevo_sender(monkeypatch):
    _enable_brevo(monkeypatch)
    monkeypatch.setattr(settings, "LOGIN_ALERT_EMAIL", "owner@example.com")
    calls = _capture_posts(monkeypatch, [(201, "{}")])
    ConsoleEmailProvider.outbox.clear()
    send_login_alert("Sospana Sonke login: Thandi", "Someone signed in.")
    assert len(calls) == 1
    assert calls[0]["payload"]["to"] == [{"email": "owner@example.com"}]
    assert ConsoleEmailProvider.outbox == []
