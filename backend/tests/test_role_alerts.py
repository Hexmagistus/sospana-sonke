"""Saved daily role alerts: validation, digest filtering, unsubscribe, migration."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.core import security
from app.core.config import settings
from app.db.migrations.role_alerts import downgrade, upgrade
from app.models.company import Company
from app.models.digest import DigestLog
from app.models.profile import CandidateProfile
from app.models.role_alert import RoleAlert
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource
from app.services.daily_digest import run_daily_digest, unsubscribe_url
from tests.conftest import register_and_login

NOW = datetime(2026, 10, 3, 6, 0, tzinfo=timezone.utc)


class Recorder:
    def __init__(self):
        self.sent: list[dict] = []

    def send(self, to, subject, body):
        self.sent.append({"to": to, "subject": subject, "body": body})
        return True


def _user(db, *, alerts=False, verified=True):
    user = User(
        email="alerts@example.com", password_hash=security.hash_password("Password123!"),
        first_name="Thandi", last_name="M", email_verified=verified, is_active=True,
        notify_opportunity_alerts=alerts,
        notify_opportunity_alerts_chosen_at=NOW - timedelta(days=2) if alerts else None,
    )
    db.add(user)
    db.flush()
    db.add(CandidateProfile(user_id=user.id, country="Kenya"))
    db.commit()
    return user


def _company(db, name, country, stype, notes="SECRET-NOTE-DO-NOT-LEAK"):
    company = Company(
        company_name=name, country=country, source_type=stype, active=True,
        careers_url=f"https://{name.lower().replace(' ', '')}.example/careers", notes=notes,
    )
    db.add(company)
    db.commit()
    source = VacancySource(company_id=company.id, url=company.careers_url, ats_type="static")
    db.add(source)
    db.commit()
    company._src = source.id
    return company


def _vac(db, company, title, *, hours_old=2, seen=None, link=None, description="SECRET-BODY-DO-NOT-LEAK"):
    seen = seen or (NOW - timedelta(hours=hours_old))
    row = Vacancy(
        company_id=company.id, source_id=company._src, title=title,
        application_url=link or f"https://jobs.example/{title.replace(' ', '-').lower()}",
        description=description, content_hash=f"h-{title}-{hours_old}",
        is_open=True, first_seen_at=seen, last_seen_at=seen, lifecycle_status="ACTIVE",
    )
    db.add(row)
    db.commit()
    return row


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_saved_alert_keeps_only_matching_new_roles_with_link_and_last_seen(db, monkeypatch):
    monkeypatch.setattr(settings, "DIGEST_DRY_RUN", False)
    user = _user(db, alerts=True)
    hospital = _company(db, "Ward Hospital", "South Africa", "HOSPITAL")
    private = _company(db, "Private Clinic", "South Africa", "PRIVATE")
    kenya = _company(db, "Nairobi Ward", "Kenya", "HOSPITAL")
    nurse = _vac(db, hospital, "Professional Nurse", link="https://ward.example/apply/nurse")
    _vac(db, private, "Professional Nurse", link="https://private.example/apply/nurse")
    _vac(db, kenya, "Professional Nurse", link="https://kenya.example/apply/nurse")
    _vac(db, hospital, "Accountant", link="https://ward.example/apply/accounts")
    db.add(RoleAlert(user_id=user.id, country="South Africa", category="HOSPITAL", keyword="nurse", active=True))
    db.commit()

    rec = Recorder()
    summary = run_daily_digest(db, now=NOW, provider=rec)
    assert summary["sent"] == 1
    body = rec.sent[0]["body"]
    assert "Professional Nurse at Ward Hospital" in body
    assert "https://ward.example/apply/nurse" in body
    assert f"last seen {nurse.last_seen_at.date().isoformat()}" in body
    assert "/preferences" in body
    assert "/notifications/digest/unsubscribe?token=" in body
    assert "/privacy" in body
    assert "one email a day" in body.lower()
    assert "if nothing new matches" in body.lower()
    for banned in ("urgent", "hurry", "act now"):
        assert banned not in body.lower()
    assert "Private Clinic" not in body
    assert "Nairobi Ward" not in body
    assert "Accountant" not in body
    assert "SECRET-NOTE" not in body and "SECRET-BODY" not in body


def test_no_email_when_nothing_matches(db, monkeypatch):
    monkeypatch.setattr(settings, "DIGEST_DRY_RUN", False)
    user = _user(db, alerts=False)
    hospital = _company(db, "Ward Hospital", "South Africa", "HOSPITAL")
    _vac(db, hospital, "Professional Nurse")
    db.add(RoleAlert(user_id=user.id, country="South Africa", category="HOSPITAL", keyword="zzzzunique", active=True))
    db.commit()
    rec = Recorder()
    summary = run_daily_digest(db, now=NOW, provider=rec)
    assert summary["sent"] == 0 and summary["empty"] == 1
    assert rec.sent == []
    assert db.query(DigestLog).count() == 0


def test_unsubscribe_pauses_saved_alerts_until_they_save_again(client, db, monkeypatch):
    monkeypatch.setattr(settings, "DIGEST_DRY_RUN", False)
    user = _user(db, alerts=True)
    hospital = _company(db, "Ward Hospital", "South Africa", "HOSPITAL")
    _vac(db, hospital, "Professional Nurse")
    db.add(RoleAlert(user_id=user.id, country="South Africa", keyword="nurse", active=True))
    db.commit()
    path = unsubscribe_url(user.id).split("/api/v1", 1)[1]
    done = client.post("/api/v1" + path)
    assert done.status_code == 200
    db.expire_all()
    paused = db.query(RoleAlert).filter(RoleAlert.user_id == user.id).one()
    assert paused.active is False
    fresh = db.get(User, user.id)
    assert fresh.notify_opportunity_alerts is False
    rec = Recorder()
    assert run_daily_digest(db, now=NOW, provider=rec)["sent"] == 0

    paused.active = True
    db.commit()
    again = run_daily_digest(db, now=NOW, provider=rec)
    assert again["sent"] == 1
    assert fresh.notify_opportunity_alerts is False


def test_validation_preview_edit_delete_and_no_notes(client, db):
    _, tokens = register_and_login(client, email="saver@example.com")
    headers = _auth(tokens)
    empty = client.post("/api/v1/alerts", headers=headers, json={})
    assert empty.status_code == 422
    bad_kw = client.post("/api/v1/alerts", headers=headers, json={"keyword": "n%"})
    assert bad_kw.status_code == 422
    short = client.post("/api/v1/alerts", headers=headers, json={"keyword": "n"})
    assert short.status_code == 422
    underscore = client.post("/api/v1/alerts", headers=headers, json={"keyword": "n_rse"})
    assert underscore.status_code == 422
    missing_country = client.post("/api/v1/alerts", headers=headers, json={"country": "Narnia", "keyword": "nurse"})
    assert missing_country.status_code == 422
    bad_cat = client.post("/api/v1/alerts", headers=headers, json={"category": "NOTACAT"})
    assert bad_cat.status_code == 422

    hospital = _company(db, "Ward Hospital", "South Africa", "HOSPITAL")
    fresh = datetime.now(timezone.utc) - timedelta(hours=1)
    older = datetime.now(timezone.utc) - timedelta(days=10)
    _vac(db, hospital, "Professional Nurse", seen=fresh, link="https://ward.example/apply/nurse")
    _vac(db, hospital, "Older Nurse", seen=older, link="https://ward.example/apply/older")

    made = client.post("/api/v1/alerts", headers=headers, json={
        "country": "South Africa", "category": "Hospital", "keyword": "nurse",
    })
    assert made.status_code == 201, made.text
    body = made.json()
    assert body["country"] == "South Africa" and body["category"] == "HOSPITAL"
    assert body["keyword"] == "nurse" and body["active"] is True
    assert "SECRET" not in made.text

    listed = client.get("/api/v1/alerts", headers=headers)
    assert listed.status_code == 200 and len(listed.json()) == 1
    person = db.query(User).filter(User.email == "saver@example.com").one()
    person.email_verified = True
    db.commit()

    preview = client.get("/api/v1/alerts/preview", headers=headers)
    assert preview.status_code == 200, preview.text
    shown = preview.json()
    assert shown["email_sent"] is False
    assert shown["would_send"] is True
    assert "SECRET-NOTE" not in preview.text and "SECRET-BODY" not in preview.text
    titles = {row["title"] for row in shown["would_email"]}
    assert titles == {"Professional Nurse"}
    assert shown["would_email"][0]["url"] == "https://ward.example/apply/nurse"
    assert shown["would_email"][0]["last_seen"]
    open_titles = {row["title"] for row in shown["open_matches"]}
    assert "Professional Nurse" in open_titles and "Older Nurse" in open_titles
    assert db.query(DigestLog).count() == 0

    edited = client.put(f"/api/v1/alerts/{body['id']}", headers=headers, json={
        "country": "South Africa", "category": "HOSPITAL", "keyword": "accountant",
    })
    assert edited.status_code == 200 and edited.json()["keyword"] == "accountant"

    other, other_tokens = register_and_login(client, email="other@example.com")
    stolen = client.delete(f"/api/v1/alerts/{body['id']}", headers=_auth(other_tokens))
    assert stolen.status_code == 404
    assert other["user"]["id"] != body["id"]

    gone = client.delete(f"/api/v1/alerts/{body['id']}", headers=headers)
    assert gone.status_code == 204
    assert client.get("/api/v1/alerts", headers=headers).json() == []

    exported = client.get("/api/v1/account/export", headers=headers)
    assert exported.status_code == 200 and exported.json()["role_alerts"] == []


def test_account_delete_removes_saved_alerts(client, db):
    _, tokens = register_and_login(client, email="gone@example.com", password="Password123!")
    headers = _auth(tokens)
    _company(db, "Ward Hospital", "South Africa", "HOSPITAL")
    made = client.post("/api/v1/alerts", headers=headers, json={"country": "South Africa", "keyword": "nurse"})
    assert made.status_code == 201
    user_id = db.query(User).filter(User.email == "gone@example.com").one().id
    deleted = client.post("/api/v1/account/delete", headers=headers, json={"password": "Password123!"})
    assert deleted.status_code == 204
    assert db.query(RoleAlert).filter(RoleAlert.user_id == user_id).count() == 0
    again = client.post("/api/v1/auth/login", json={"email": "gone@example.com", "password": "Password123!"})
    assert again.status_code == 401


def test_role_alerts_migration_upgrades_and_rolls_back():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    upgrade(engine)
    upgrade(engine)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO role_alerts (id, user_id, country, keyword, active) "
            "VALUES ('a1', 'user-1', 'South Africa', 'nurse', 1)"
        ))
        assert conn.execute(text("SELECT keyword FROM role_alerts")).scalar() == "nurse"
    downgrade(engine)
    assert "role_alerts" not in inspect(engine).get_table_names()
    upgrade(engine)
    assert "role_alerts" in inspect(engine).get_table_names()
    with engine.begin() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM role_alerts")).scalar() == 0
    engine.dispose()
