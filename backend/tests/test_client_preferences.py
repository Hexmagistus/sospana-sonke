"""Client preferences: tagging, preferred post, alerts. Each has its own chosen state."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.admin_ops import AdminAuditLog
from app.models.notification import Notification
from app.models.profile import CandidateProfile
from app.models.user import POST_TYPES, User
from app.notifications.email import ConsoleEmailProvider
from app.services import preference_mail
from app.services.preference_mail import _FORBIDDEN, preferences_url, service_email_body
from tests.conftest import make_admin, register_and_login, admin_login

PW = "Password123!"


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _admin(client, db_engine):
    email, password = make_admin(db_engine)
    return admin_login(client, email, password).json()


def _all(tagging: bool, post: str, alerts: bool) -> dict:
    return {"allow_tagging": tagging, "preferred_post_type": post, "notify_opportunity_alerts": alerts}


def _session(db_engine):
    return sessionmaker(bind=db_engine)()


def _mailed(to):
    return [m for m in ConsoleEmailProvider.outbox if m["to"] == to]


# ---- (1) separate "has chosen" state --------------------------------------

def test_new_account_has_all_three_not_chosen(client):
    reg, tokens = register_and_login(client, email="fresh@example.com")
    me = client.get("/api/v1/auth/me", headers=_auth(tokens)).json()
    assert me["tagging_state"] == "not_chosen"
    assert me["preferred_post_state"] == "not_chosen"
    assert me["alerts_state"] == "not_chosen"
    assert me["preferred_post_type"] is None
    assert me["show_consent_banner"] is True


def test_each_preference_is_recorded_on_its_own(client, db_engine):
    reg, tokens = register_and_login(client, email="one-at-a-time@example.com")
    h = _auth(tokens)
    r = client.put("/api/v1/account/notification-preferences", headers=h, json={"allow_tagging": False})
    assert r.status_code == 200, r.text
    body = r.json()
    # An explicit "no" is a choice; the other two are untouched.
    assert body["tagging_state"] == "no"
    assert body["preferred_post_state"] == "not_chosen"
    assert body["alerts_state"] == "not_chosen"
    assert body["show_consent_banner"] is True

    r = client.put("/api/v1/account/notification-preferences", headers=h,
                   json={"preferred_post_type": "contract"})
    assert r.json()["preferred_post_state"] == "chosen"
    assert r.json()["preferred_post_type"] == "contract"
    assert r.json()["alerts_state"] == "not_chosen"
    assert r.json()["show_consent_banner"] is True

    r = client.put("/api/v1/account/notification-preferences", headers=h,
                   json={"notify_opportunity_alerts": True})
    assert r.json()["alerts_state"] == "yes"
    assert r.json()["tagging_state"] == "no"
    assert r.json()["show_consent_banner"] is False

    s = _session(db_engine)
    try:
        u = s.get(User, reg["user"]["id"])
        assert u.allow_tagging_chosen_at and u.preferred_post_chosen_at
        assert u.notify_opportunity_alerts_chosen_at
    finally:
        s.close()


def test_a_no_is_different_from_not_chosen_and_validation(client):
    _, tokens = register_and_login(client, email="validate@example.com")
    h = _auth(tokens)
    bad = client.put("/api/v1/account/notification-preferences", headers=h,
                     json={"preferred_post_type": "astronaut"})
    assert bad.status_code == 422
    empty = client.put("/api/v1/account/notification-preferences", headers=h, json={})
    assert empty.status_code == 422
    none_post = client.put("/api/v1/account/notification-preferences", headers=h,
                           json={"preferred_post_type": "none"})
    assert none_post.json()["preferred_post_state"] == "chosen"   # "none" is a real answer
    assert set(POST_TYPES) >= {"any", "permanent", "contract", "none"}


def test_register_records_only_the_choices_that_were_sent(client):
    reg, _ = register_and_login(client, email="partial@example.com", allow_tagging=False)
    assert reg["user"]["tagging_state"] == "no"
    assert reg["user"]["preferred_post_state"] == "not_chosen"
    assert reg["user"]["alerts_state"] == "not_chosen"
    reg2, tokens2 = register_and_login(client, email="all3@example.com", **_all(True, "graduate", False))
    assert reg2["user"]["tagging_state"] == "yes"
    assert reg2["user"]["preferred_post_state"] == "chosen"
    assert reg2["user"]["alerts_state"] == "no"
    assert reg2["user"]["show_consent_banner"] is False
    notes = [n for n in client.get("/api/v1/notifications", headers=_auth(tokens2)).json()
             if n["type"] == "consent_choices"]
    assert notes == []


def test_legacy_alerts_yes_counts_as_chosen(db):
    u = User(email="legacy@example.com", password_hash="x", first_name="L", last_name="U",
             notify_opportunity_alerts=True)
    assert u.alerts_state == "yes"
    assert u.tagging_state == "not_chosen"


def test_export_includes_the_chosen_state(client):
    _, tokens = register_and_login(client, email="exp@example.com", **_all(True, "any", False))
    acct = client.get("/api/v1/account/export", headers=_auth(tokens)).json()["account"]
    assert acct["allow_tagging"] is True and acct["allow_tagging_chosen_at"]
    assert acct["preferred_post_type"] == "any" and acct["preferred_post_chosen_at"]
    assert acct["notify_opportunity_alerts_chosen_at"]


def test_delete_clears_the_preferences(client, db_engine):
    reg, tokens = register_and_login(client, email="erase@example.com", **_all(True, "any", True))
    gone = client.post("/api/v1/account/delete", headers=_auth(tokens), json={"password": PW})
    assert gone.status_code == 204
    s = _session(db_engine)
    try:
        p = s.get(User, reg["user"]["id"])
        assert p.allow_tagging is False and p.allow_tagging_chosen_at is None
        assert p.preferred_post_type is None and p.preferred_post_chosen_at is None
        assert p.notify_opportunity_alerts_chosen_at is None
        assert p.consent_prompt_sent_at is None
    finally:
        s.close()


# ---- (3) banner: only choosing removes it --------------------------------

def test_banner_has_no_dismiss_and_clears_only_when_all_three_chosen(client):
    _, tokens = register_and_login(client, email="banner@example.com")
    h = _auth(tokens)
    assert client.post("/api/v1/account/tagging-banner/dismiss", headers=h).status_code in (404, 405)
    assert client.get("/api/v1/auth/me", headers=h).json()["show_consent_banner"] is True
    client.put("/api/v1/account/notification-preferences", headers=h,
               json={"allow_tagging": True, "preferred_post_type": "any"})
    assert client.get("/api/v1/auth/me", headers=h).json()["show_consent_banner"] is True
    client.put("/api/v1/account/notification-preferences", headers=h,
               json={"notify_opportunity_alerts": False})
    assert client.get("/api/v1/auth/me", headers=h).json()["show_consent_banner"] is False


def test_admin_never_sees_the_banner(client, db_engine):
    admin = _admin(client, db_engine)
    me = client.get("/api/v1/auth/me", headers=_auth(admin)).json()
    assert me["show_consent_banner"] is False


def test_login_stores_one_notice_pointing_at_preferences_and_settles_it(client):
    _, tokens = register_and_login(client, email="notice@example.com")
    h = _auth(tokens)
    client.post("/api/v1/auth/login", json={"email": "notice@example.com", "password": PW})
    notes = [n for n in client.get("/api/v1/notifications", headers=h).json()
             if n["type"] == "consent_choices"]
    assert len(notes) == 1
    assert notes[0]["link_url"] == "/preferences"
    assert notes[0]["email_sent"] is False
    client.put("/api/v1/account/notification-preferences", headers=h, json=_all(False, "none", False))
    notes = [n for n in client.get("/api/v1/notifications", headers=h).json()
             if n["type"] == "consent_choices"]
    assert notes[0]["is_read"] is True


# ---- tagging requires an explicit yes ------------------------------------

def test_admin_can_only_tag_people_who_said_yes(client, db_engine):
    admin = _admin(client, db_engine)
    yes, _ = register_and_login(client, email="yes@example.com", allow_tagging=True)
    no, _ = register_and_login(client, email="no@example.com", allow_tagging=False)
    unset, _ = register_and_login(client, email="unset@example.com")
    for person, code in ((yes, 200), (no, 403), (unset, 403)):
        r = client.post(f"/api/v1/admin/users/{person['user']['id']}/tags",
                        headers=_auth(admin), json={"tag": "kitchen"})
        assert r.status_code == code, (person["user"]["email"], r.text)


def test_inactive_account_cannot_be_tagged(client, db_engine):
    admin = _admin(client, db_engine)
    reg, _ = register_and_login(client, email="inactive-tag@example.com", allow_tagging=True)
    s = _session(db_engine)
    try:
        s.get(User, reg["user"]["id"]).is_active = False
        s.commit()
    finally:
        s.close()
    denied = client.post(f"/api/v1/admin/users/{reg['user']['id']}/tags",
                         headers=_auth(admin), json={"tag": "kitchen"})
    assert denied.status_code == 403


# ---- (4) one-time service email ------------------------------------------

def test_service_email_wording():
    body = service_email_body()
    low = body.lower()
    assert "Sospana Sonke" in body
    assert preferences_url() in body and preferences_url().endswith("/preferences")
    assert not any(word in low for word in _FORBIDDEN)
    # POPIA / unsubscribe wording
    assert "POPIA" in body
    assert "one-time message" in body
    assert "choose No" in body and "delete your account" in body
    assert "Privacy Policy" in body
    # nothing but our own two links
    assert body.count("http") == 2


def test_dry_run_counts_then_send_goes_once_and_only_to_unchosen(client, db_engine):
    admin = _admin(client, db_engine)
    register_and_login(client, email="needs-choice@example.com")
    register_and_login(client, email="half@example.com", allow_tagging=True)
    register_and_login(client, email="all-set@example.com", **_all(False, "none", False))
    ConsoleEmailProvider.outbox.clear()

    counted = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                          json={"dry_run": True, "batch": 40})
    assert counted.status_code == 200, counted.text
    assert counted.json()["eligible"] == 2
    assert counted.json()["would_send"] == 2
    assert counted.json()["sent"] == 0
    assert ConsoleEmailProvider.outbox == []

    sent = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                       json={"dry_run": False, "batch": 40})
    assert sent.status_code == 200, sent.text
    assert sent.json()["sent"] == 2
    assert len(_mailed("needs-choice@example.com")) == 1
    assert len(_mailed("half@example.com")) == 1
    assert _mailed("all-set@example.com") == []
    assert _mailed("admin@example.com") == []
    msg = _mailed("needs-choice@example.com")[0]
    assert not any(w in msg["body"].lower() for w in _FORBIDDEN)

    again = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                        json={"dry_run": False, "batch": 40})
    assert again.json()["sent"] == 0 and again.json()["eligible"] == 0
    assert len(_mailed("needs-choice@example.com")) == 1

    s = _session(db_engine)
    try:
        audits = s.query(AdminAuditLog).filter(AdminAuditLog.action == "preference_email").all()
        assert audits and all("@" not in (a.detail or "") for a in audits)
    finally:
        s.close()


def test_a_person_who_chooses_after_the_count_is_not_emailed(client, db_engine):
    admin = _admin(client, db_engine)
    _, tokens = register_and_login(client, email="quick@example.com")
    client.put("/api/v1/account/notification-preferences", headers=_auth(tokens),
               json=_all(True, "any", True))
    ConsoleEmailProvider.outbox.clear()
    r = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                    json={"dry_run": False, "batch": 40})
    assert r.json()["sent"] == 0
    assert _mailed("quick@example.com") == []


def test_users_with_no_email_are_skipped(client, db_engine):
    admin = _admin(client, db_engine)
    s = _session(db_engine)
    try:
        for i, addr in enumerate(["", "   ", "not-an-address"]):
            s.add(User(email=addr or f"blank{i}", password_hash="x", first_name="N", last_name="E"))
        s.commit()
        # make them blank after insert (the column is unique and not null)
        rows = s.query(User).filter(User.first_name == "N").order_by(User.created_at).all()
        rows[0].email, rows[1].email = "", "   "
        s.commit()
    finally:
        s.close()
    register_and_login(client, email="real@example.com")
    ConsoleEmailProvider.outbox.clear()
    counted = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                          json={"dry_run": True}).json()
    assert counted["eligible"] == 1
    assert counted["skipped_no_email"] == 3
    sent = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                       json={"dry_run": False}).json()
    assert sent["sent"] == 1
    assert [m["to"] for m in ConsoleEmailProvider.outbox] == ["real@example.com"]


def test_daily_cap_stops_the_batch_and_it_resumes_after_24_hours(client, db_engine, monkeypatch):
    monkeypatch.setattr(preference_mail, "PREFERENCE_EMAIL_DAILY_CAP", 2)
    admin = _admin(client, db_engine)
    for n in range(4):
        register_and_login(client, email=f"cap{n}@example.com")
    ConsoleEmailProvider.outbox.clear()
    post = lambda dry: client.post("/api/v1/admin/preference-email", headers=_auth(admin),  # noqa: E731
                                   json={"dry_run": dry, "batch": 40})
    first = post(False).json()
    assert first["sent"] == 2 and first["eligible"] == 2 and first["remaining_today"] == 0
    assert len(ConsoleEmailProvider.outbox) == 2

    blocked = post(False).json()
    assert blocked["sent"] == 0 and blocked["would_send"] == 0 and blocked["resume_at"]
    assert len(ConsoleEmailProvider.outbox) == 2

    s = _session(db_engine)
    try:
        for u in s.query(User).filter(User.consent_prompt_sent_at.isnot(None)).all():
            u.consent_prompt_sent_at = datetime.now(timezone.utc) - timedelta(hours=25)
        s.commit()
    finally:
        s.close()
    resumed = post(False).json()
    assert resumed["sent"] == 2 and resumed["eligible"] == 0
    recipients = [m["to"] for m in ConsoleEmailProvider.outbox]
    assert len(recipients) == 4 and len(set(recipients)) == 4   # nobody twice


def test_other_mail_in_the_last_24h_uses_up_the_shared_daily_limit(client, db_engine, monkeypatch):
    monkeypatch.setattr(preference_mail, "PREFERENCE_EMAIL_DAILY_CAP", 3)
    admin = _admin(client, db_engine)
    reg, _ = register_and_login(client, email="target@example.com")
    s = _session(db_engine)
    try:
        for _ in range(3):
            s.add(Notification(user_id=reg["user"]["id"], type="system", title="t", body="b",
                               email_sent=True))
        s.commit()
    finally:
        s.close()
    counted = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                          json={"dry_run": True}).json()
    assert counted["remaining_today"] == 0 and counted["would_send"] == 0


def test_batch_never_exceeds_50_and_default_cap_is_under_brevo_limit():
    assert preference_mail.MAX_BATCH <= 50
    assert preference_mail.PREFERENCE_EMAIL_DAILY_CAP < preference_mail.BREVO_FREE_DAILY_LIMIT == 300


def test_batch_size_is_validated(client, db_engine):
    admin = _admin(client, db_engine)
    r = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                    json={"dry_run": True, "batch": 500})
    assert r.status_code == 422


def test_failed_send_releases_the_claim_and_stops(client, db_engine, monkeypatch):
    admin = _admin(client, db_engine)
    register_and_login(client, email="retry1@example.com")
    register_and_login(client, email="retry2@example.com")
    calls = []

    def _fail(self, to, subject, body):
        calls.append(to)
        return False

    monkeypatch.setattr(ConsoleEmailProvider, "send", _fail)
    failed = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                         json={"dry_run": False}).json()
    assert failed["sent"] == 0 and failed["failed"] == 2 and failed["eligible"] == 2
    assert len(calls) == 1   # stopped at the first failure; the provider is not hammered


def test_concurrent_claim_cannot_double_send(client, db_engine, monkeypatch):
    """If another request already claimed a person, this one skips them."""
    admin = _admin(client, db_engine)
    reg, _ = register_and_login(client, email="raced@example.com")
    real = preference_mail._next_batch_ids

    def stale_ids(db, n):
        ids = real(db, n)
        s = _session(db_engine)
        try:
            s.get(User, reg["user"]["id"]).consent_prompt_sent_at = datetime.now(timezone.utc)
            s.commit()
        finally:
            s.close()
        return ids

    monkeypatch.setattr(preference_mail, "_next_batch_ids", stale_ids)
    ConsoleEmailProvider.outbox.clear()
    out = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                      json={"dry_run": False}).json()
    assert out["sent"] == 0
    assert _mailed("raced@example.com") == []


def test_queue_order_is_south_africa_then_sadc_then_africa_then_rest(client, db_engine):
    admin = _admin(client, db_engine)
    order = [("Germany", "e-de"), ("Kenya", "d-ke"), ("Zambia", "b-zm"), ("South Africa", "a-za")]
    ids = {}
    for country, label in order:      # created in the "wrong" order on purpose
        reg, _ = register_and_login(client, email=f"{label}@example.com")
        ids[label] = reg["user"]["id"]
    s = _session(db_engine)
    try:
        for country, label in order:
            s.add(CandidateProfile(user_id=ids[label], country=country))
        s.commit()
    finally:
        s.close()
    ConsoleEmailProvider.outbox.clear()
    out = client.post("/api/v1/admin/preference-email", headers=_auth(admin),
                      json={"dry_run": False}).json()
    assert out["sent"] == 4
    assert [m["to"] for m in ConsoleEmailProvider.outbox] == [
        "a-za@example.com", "b-zm@example.com", "d-ke@example.com", "e-de@example.com"]


def test_service_email_is_admin_only(client):
    _, tokens = register_and_login(client, email="not-admin@example.com")
    assert client.post("/api/v1/admin/preference-email", headers=_auth(tokens),
                       json={"dry_run": True}).status_code == 403
    assert client.post("/api/v1/admin/preference-email", json={"dry_run": True}).status_code in (401, 403)


def test_the_route_is_rate_limited():
    from app.api import routes_notifications
    route = next(r for r in routes_notifications.router.routes
                 if getattr(r, "path", "") == "/admin/preference-email")
    assert getattr(route.endpoint, "__wrapped__", None) is not None   # slowapi wraps it


# ---- migration: additive, safe on a table that already exists ---------------

NEW_USER_COLUMNS = {
    "allow_tagging", "allow_tagging_chosen_at", "preferred_post_type", "preferred_post_chosen_at",
    "notify_opportunity_alerts_chosen_at", "consent_prompt_sent_at",
    "admin_login_digest", "admin_login_digest_sent_at",
}


def test_boot_adds_the_new_columns_to_an_existing_users_table(tmp_path, monkeypatch):
    """The repo has no Alembic: startup runs additive ALTER TABLE ADD COLUMN. An old
    users table gets the new columns, existing rows read as 'not chosen', and a
    second boot changes nothing."""
    from sqlalchemy import create_engine, inspect, text

    from app.db import session as db_session

    registered = {c for t, c, _ in db_session._NEW_COLUMNS if t == "users"}
    assert NEW_USER_COLUMNS <= registered
    # additive only: no drops, no type rewrites in what we registered
    for table, column, ddl in db_session._NEW_COLUMNS:
        assert "DROP" not in ddl.upper()

    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255), "
                          "notify_opportunity_alerts BOOLEAN DEFAULT 1)"))
        conn.execute(text("INSERT INTO users (id, email, notify_opportunity_alerts) VALUES ('u1', 'a@b.co', 1)"))
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "_is_sqlite", True)

    db_session._add_new_columns()
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    assert NEW_USER_COLUMNS <= cols
    with engine.begin() as conn:
        row = conn.execute(text("SELECT allow_tagging, allow_tagging_chosen_at, preferred_post_type, "
                                "admin_login_digest, notify_opportunity_alerts FROM users")).one()
    assert row[0] == 0 and row[1] is None and row[2] is None and row[3] == 0
    assert row[4] == 1          # nothing existing was rewritten
    db_session._add_new_columns()   # idempotent
    assert {c["name"] for c in inspect(engine).get_columns("users")} == cols
