"""The daily digest: one email per opted-in user per day, never empty, capped, ordered."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core import security
from app.core.config import settings
from app.models.company import Company
from app.models.digest import DigestLog
from app.models.notification import Notification
from app.models.profile import CandidateProfile
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource
from app.models.watch import CompanyWatch
from app.notifications.email import ConsoleEmailProvider, _html_from_text
from app.services.daily_digest import (
    build_content, digest_day, render_digest, run_daily_digest, unsubscribe_url,
)

# 09:00 SAST on a Saturday = 07:00 UTC; the cron fires at 06:00 UTC.
NOW = datetime(2026, 10, 3, 6, 0, tzinfo=timezone.utc)


class Recorder:
    """A fake provider: records sends, can be told to fail."""
    def __init__(self, ok=True):
        self.sent: list[dict] = []
        self.ok = ok

    def send(self, to, subject, body):
        if not self.ok:
            return False
        self.sent.append({"to": to, "subject": subject, "body": body})
        return True


_n = {"i": 0}


def _user(db, email=None, *, alerts=True, country="South Africa", verified=True, active=True,
          tagging=False, relocate=False, post=None, first="Thandi", created=None, **extra):
    _n["i"] += 1
    email = email or f"u{_n['i']}@example.com"
    u = User(email=email, password_hash=security.hash_password("Password123!"),
             first_name=first, last_name="M", email_verified=verified, is_active=active,
             notify_opportunity_alerts=alerts,
             notify_opportunity_alerts_chosen_at=NOW - timedelta(days=30) if alerts else None,
             allow_tagging=tagging,
             allow_tagging_chosen_at=NOW - timedelta(days=30) if tagging else None,
             **extra)
    if post:
        u.preferred_post_type = post
        u.preferred_post_chosen_at = NOW - timedelta(days=30)
    db.add(u)
    db.flush()
    if created:
        u.created_at = created
    db.add(CandidateProfile(user_id=u.id, country=country, willing_to_relocate=relocate))
    db.commit()
    return u


def _company(db, name="Acme", country="South Africa", careers="https://acme.example/careers", stype="JSE"):
    c = Company(company_name=name, country=country, careers_url=careers, source_type=stype, active=True)
    db.add(c)
    db.commit()
    src = VacancySource(company_id=c.id, url=careers or "https://x.example", ats_type="static")
    db.add(src)
    db.commit()
    c._src = src.id
    return c


_v = {"i": 0}


def _vac(db, company, title="Analyst", hours_old=2, link="https://acme.example/apply/1", **kw):
    _v["i"] += 1
    seen = NOW - timedelta(hours=hours_old)
    v = Vacancy(company_id=company.id, source_id=company._src, title=title, application_url=link,
                content_hash=f"h{_v['i']}", is_open=True, first_seen_at=seen, last_seen_at=seen, **kw)
    db.add(v)
    db.commit()
    return v


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    monkeypatch.setattr(settings, "DIGEST_DAILY_SEND_CAP", 250)
    monkeypatch.setattr(settings, "DIGEST_DRY_RUN", False)
    monkeypatch.setattr(settings, "DIGEST_MAX_ITEMS", 25)
    monkeypatch.setattr(settings, "DIGEST_LOOKBACK_HOURS", 24)


# ---------------------------------------------------------------- idempotency

def test_one_digest_per_user_per_day_even_if_cron_fires_twice(db):
    u = _user(db)
    c = _company(db)
    _vac(db, c, "Data Analyst")
    rec = Recorder()
    first = run_daily_digest(db, now=NOW, provider=rec)
    second = run_daily_digest(db, now=NOW + timedelta(hours=3), provider=rec)
    assert first["sent"] == 1 and second["sent"] == 0
    assert len(rec.sent) == 1
    assert rec.sent[0]["to"] == u.email
    rows = db.query(DigestLog).all()
    assert len(rows) == 1 and rows[0].status == "sent" and rows[0].digest_date == "2026-10-03"


def test_a_second_vacancy_later_the_same_day_does_not_trigger_a_second_email(db):
    _user(db)
    c = _company(db)
    _vac(db, c, "First")
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    _vac(db, c, "Second", hours_old=0, link="https://acme.example/apply/2")
    run_daily_digest(db, now=NOW + timedelta(hours=5), provider=rec)
    assert len(rec.sent) == 1


def test_next_day_sends_again_and_window_continues_from_the_last_digest(db):
    _user(db)
    c = _company(db)
    _vac(db, c, "Monday role", hours_old=2)
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    tomorrow = NOW + timedelta(days=1)
    _vac(db, c, "Tuesday role", hours_old=1, link="https://acme.example/apply/9")
    # the Tuesday row is first seen at NOW-1h (before today's 06:00 + 24h - 1h?) -> make it clearly new
    v = db.query(Vacancy).filter(Vacancy.title == "Tuesday role").one()
    v.first_seen_at = tomorrow - timedelta(hours=1)
    db.commit()
    out = run_daily_digest(db, now=tomorrow, provider=rec)
    assert out["sent"] == 1 and len(rec.sent) == 2
    assert "Tuesday role" in rec.sent[1]["body"] and "Monday role" not in rec.sent[1]["body"]


def test_day_is_the_south_africa_day(db):
    assert digest_day(datetime(2026, 10, 3, 21, 59, tzinfo=timezone.utc)) == "2026-10-03"
    assert digest_day(datetime(2026, 10, 3, 22, 0, tzinfo=timezone.utc)) == "2026-10-04"


def test_a_failed_send_releases_the_claim_and_stops_the_run(db):
    for _ in range(3):
        _user(db)
    c = _company(db)
    _vac(db, c)
    bad = Recorder(ok=False)
    out = run_daily_digest(db, now=NOW, provider=bad)
    assert out["failed"] == 1 and out["sent"] == 0       # stopped at the first failure
    assert db.query(DigestLog).count() == 0
    good = Recorder()
    out2 = run_daily_digest(db, now=NOW + timedelta(minutes=30), provider=good)
    assert out2["sent"] == 3 and len(good.sent) == 3


def test_existing_claim_blocks_a_second_send(db):
    u = _user(db)
    c = _company(db)
    _vac(db, c)
    db.add(DigestLog(user_id=u.id, digest_date="2026-10-03", status="claimed"))
    db.commit()
    rec = Recorder()
    assert run_daily_digest(db, now=NOW, provider=rec)["sent"] == 0
    assert rec.sent == []


# ---------------------------------------------------------------- no empty digests

def test_users_with_nothing_new_get_no_email_and_no_log(db):
    _user(db)
    c = _company(db)
    _vac(db, c, "Old role", hours_old=30)       # outside the 24h window
    rec = Recorder()
    out = run_daily_digest(db, now=NOW, provider=rec)
    assert out["sent"] == 0 and out["empty"] == 1
    assert rec.sent == [] and db.query(DigestLog).count() == 0


def test_closed_duplicate_and_deleted_vacancies_are_not_listed(db):
    u = _user(db)
    c = _company(db)
    keep = _vac(db, c, "Keep me")
    closed = _vac(db, c, "Closed one", link="https://acme.example/apply/c")
    closed.is_open = False
    dup = _vac(db, c, "Dup one", link="https://acme.example/apply/d")
    dup.duplicate_of_id = keep.id
    gone = _vac(db, c, "Deleted one", link="https://acme.example/apply/x")
    gone.deleted_at = NOW
    db.commit()
    body = render_digest(u, build_content(db, u, since=NOW - timedelta(hours=24), until=NOW),
                         now=NOW, max_items=25)[1]
    assert "Keep me" in body
    for t in ("Closed one", "Dup one", "Deleted one"):
        assert t not in body


# ---------------------------------------------------------------- opt-in (POPIA)

def test_only_verified_active_opted_in_users_are_emailed(db):
    yes = _user(db, "yes@example.com")
    _user(db, "no-alerts@example.com", alerts=False)
    _user(db, "unverified@example.com", verified=False)
    _user(db, "inactive@example.com", active=False)
    gone = _user(db, "deleted@example.com")
    gone.deleted_at = NOW
    admin = _user(db, "admin@example.com")
    admin.role = "admin"
    db.commit()
    c = _company(db)
    _vac(db, c)
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    assert [m["to"] for m in rec.sent] == [yes.email]


def test_unsubscribed_users_stay_off_until_they_choose_again(db):
    u = _user(db)
    u.digest_unsubscribed_at = NOW - timedelta(days=2)
    u.notify_opportunity_alerts_chosen_at = NOW - timedelta(days=2)
    db.commit()
    c = _company(db)
    _vac(db, c)
    rec = Recorder()
    assert run_daily_digest(db, now=NOW, provider=rec)["sent"] == 0
    u.notify_opportunity_alerts_chosen_at = NOW - timedelta(hours=5)   # chose alerts again
    db.commit()
    assert run_daily_digest(db, now=NOW, provider=rec)["sent"] == 1


def test_tagging_only_user_gets_tagged_posts_but_no_openings(db):
    u = _user(db, alerts=False, tagging=True)
    c = _company(db)
    _vac(db, c, "Open role the user did not ask alerts for")
    db.add(Notification(user_id=u.id, type="admin_suggestion", title="Ward clerk at Acme",
                        body="Hi\n\nTagged by the Sospana Sonke team.\nEmployer: Acme",
                        link_url="https://apply.example.com/clerk", created_at=NOW - timedelta(hours=3)))
    db.add(Notification(user_id=_user(db, alerts=False, tagging=False).id, type="admin_suggestion",
                        title="Not for this person", body="x", link_url="https://x.example/",
                        created_at=NOW - timedelta(hours=3)))
    db.commit()
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    assert len(rec.sent) == 1
    body = rec.sent[0]["body"]
    assert "Ward clerk at Acme" in body and "https://apply.example.com/clerk" in body
    assert "Open role the user did not ask" not in body


def test_watch_only_user_gets_page_change_notice(db):
    u = _user(db, alerts=False)
    c = _company(db)
    db.add(CompanyWatch(user_id=u.id, company_id=c.id, active=True))
    db.add(Notification(user_id=u.id, type="link_updated", title="Acme's careers page was updated",
                        body="changed", link_url=c.careers_url, created_at=NOW - timedelta(hours=2)))
    db.commit()
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    assert len(rec.sent) == 1
    assert "Acme's careers page was updated" in rec.sent[0]["body"]
    assert c.careers_url in rec.sent[0]["body"]


def test_legacy_match_and_agent_notices_are_not_mailed_and_no_matches_section(db):
    """Matching is gone: old strong_match / daily_agent_briefing rows and old CandidateMatch rows
    stay in the DB but never reach the digest, which has no match or agent section."""
    from app.models.match import CandidateMatch
    u = _user(db)
    c = _company(db)
    v = _vac(db, c, "Strong fit role")
    db.add(CandidateMatch(user_id=u.id, vacancy_id=v.id, score=88.0, band="Strong",
                          created_at=NOW - timedelta(hours=3)))
    db.add(Notification(user_id=u.id, type="daily_agent_briefing",
                        title="Your daily agent found 3 new applications to review", body="x",
                        created_at=NOW - timedelta(hours=4)))
    db.add(Notification(user_id=u.id, type="strong_match", title="Strong match: Old Role", body="x",
                        created_at=NOW - timedelta(hours=4)))
    db.commit()
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    assert len(rec.sent) == 1
    body = rec.sent[0]["body"]
    assert body.count("Strong fit role") == 1          # a plain new opening, listed once
    assert "% match" not in body and "STRONG MATCHES" not in body.upper()
    assert "PREPARED BY YOUR DAILY AGENT" not in body.upper()
    assert "found 3 new applications" not in body and "Old Role" not in body
    assert db.query(CandidateMatch).count() == 1        # stored data untouched


def test_digest_only_lists_vacancies_first_seen_in_the_last_24h(db):
    u = _user(db)
    c = _company(db)
    _vac(db, c, "Fresh Role", hours_old=3)
    _vac(db, c, "Last Week Role", hours_old=24 * 7, link="https://acme.example/apply/old")
    body = render_digest(u, build_content(db, u, since=NOW - timedelta(days=30), until=NOW),
                         now=NOW, max_items=25)[1]
    assert "Fresh Role" in body and "Last Week Role" not in body   # even a wide window is clamped


def test_digest_window_never_reaches_back_over_24h(db):
    """A user whose previous digest was 40h ago (missed run) still only gets the last 24h."""
    u = _user(db)
    c = _company(db)
    _vac(db, c, "Fresh Role", hours_old=5)
    _vac(db, c, "Missed Yesterday", hours_old=30, link="https://acme.example/apply/m")
    db.add(DigestLog(user_id=u.id, digest_date="2026-10-01", status="sent",
                     window_start=NOW - timedelta(hours=64), window_end=NOW - timedelta(hours=40),
                     sent_at=NOW - timedelta(hours=40)))
    db.commit()
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    assert len(rec.sent) == 1
    assert "Fresh Role" in rec.sent[0]["body"] and "Missed Yesterday" not in rec.sent[0]["body"]


def test_digest_skips_reposted_old_posts_and_closed_ones(db):
    """Re-discovered old adverts (posting date days ago) or already-closed ones are not "new"."""
    u = _user(db)
    c = _company(db)
    today = NOW.date()
    _vac(db, c, "Genuinely New", posting_date=today)
    _vac(db, c, "Undated New", link="https://acme.example/apply/u")
    _vac(db, c, "Old Post Rediscovered", posting_date=today - timedelta(days=30),
         link="https://acme.example/apply/o")
    _vac(db, c, "Already Closed", closing_date=today - timedelta(days=1),
         link="https://acme.example/apply/c")
    body = render_digest(u, build_content(db, u, since=NOW - timedelta(hours=24), until=NOW),
                         now=NOW, max_items=25)[1]
    assert "Genuinely New" in body and "Undated New" in body
    assert "Old Post Rediscovered" not in body and "Already Closed" not in body


def test_every_digest_has_unsubscribe_and_preferences_links(db):
    u = _user(db)
    c = _company(db)
    _vac(db, c)
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    body = rec.sent[0]["body"]
    assert "/preferences" in body
    assert "/api/v1/notifications/digest/unsubscribe?token=" in body
    assert "/privacy" in body
    assert rec.sent[0]["subject"].startswith("Your daily updates")
    assert body.startswith("Your daily updates")
    html = _html_from_text(body)
    assert ">Unsubscribe</a>" in html and "View careers page" in html


def test_unsubscribe_link_get_changes_nothing_post_switches_off(client, db):
    u = _user(db)
    url = unsubscribe_url(u.id)
    path = url.split("/api/v1", 1)[1]
    page = client.get("/api/v1" + path)
    assert page.status_code == 200 and "<form" in page.text
    db.refresh(u)
    assert u.notify_opportunity_alerts is True and u.digest_unsubscribed_at is None
    done = client.post("/api/v1" + path)
    assert done.status_code == 200 and "unsubscribed" in done.text.lower()
    db.expire_all()
    u = db.get(User, u.id)
    assert u.notify_opportunity_alerts is False and u.digest_unsubscribed_at is not None
    c = _company(db)
    _vac(db, c)
    rec = Recorder()
    assert run_daily_digest(db, now=datetime.now(timezone.utc), provider=rec)["sent"] == 0
    bad = client.post("/api/v1/notifications/digest/unsubscribe?token=nonsense")
    assert bad.status_code == 400


# ---------------------------------------------------------------- content, scope and ordering

def test_scope_follows_the_profile_country_unless_willing_to_relocate(db):
    sa = _user(db, "sa@example.com", country="South Africa")
    mover = _user(db, "mover@example.com", country="South Africa", relocate=True)
    c_sa = _company(db, "Sa Co", "South Africa")
    c_ke = _company(db, "Ke Co", "Kenya", "https://ke.example/careers")
    _vac(db, c_sa, "SA role", link="https://sa.example/1")
    _vac(db, c_ke, "Kenya role", link="https://ke.example/1")
    rec = Recorder()
    run_daily_digest(db, now=NOW, provider=rec)
    by = {m["to"]: m["body"] for m in rec.sent}
    assert "SA role" in by[sa.email] and "Kenya role" not in by[sa.email]
    assert "SA role" in by[mover.email] and "Kenya role" in by[mover.email]


def test_openings_are_grouped_south_africa_then_sadc_then_africa_then_other(db):
    u = _user(db, relocate=True)
    for name, country, link in (("Us Co", "United States", "https://us.example/1"),
                                ("Ke Co", "Kenya", "https://ke.example/1"),
                                ("Bw Co", "Botswana", "https://bw.example/1"),
                                ("Sa Co", "South Africa", "https://sa.example/1")):
        _vac(db, _company(db, name, country, link), f"{name} role", link=link)
    body = render_digest(u, build_content(db, u, since=NOW - timedelta(hours=24), until=NOW),
                         now=NOW, max_items=25)[1]
    order = [body.index(x) for x in ("NEW OPENINGS: SOUTH AFRICA", "NEW OPENINGS: REST OF SADC",
                                      "NEW OPENINGS: REST OF AFRICA", "NEW OPENINGS: OTHER REGIONS")]
    assert order == sorted(order)
    assert body.index("Sa Co role") < body.index("Bw Co role") < body.index("Ke Co role") < body.index("Us Co role")


def test_users_are_served_south_africa_first_when_the_cap_bites(db, monkeypatch):
    monkeypatch.setattr(settings, "DIGEST_DAILY_SEND_CAP", 2)
    us = _user(db, "us@example.com", country="United States", relocate=True,
               created=NOW - timedelta(days=900))
    ke = _user(db, "ke@example.com", country="Kenya", relocate=True, created=NOW - timedelta(days=800))
    za1 = _user(db, "za1@example.com", created=NOW - timedelta(days=10))
    za2 = _user(db, "za2@example.com", created=NOW - timedelta(days=5))
    _vac(db, _company(db), "Role")
    rec = Recorder()
    out = run_daily_digest(db, now=NOW, provider=rec)
    assert [m["to"] for m in rec.sent] == [za1.email, za2.email]
    assert out["sent"] == 2 and out["capped"] == 2


def test_direct_vacancy_link_is_used_else_the_careers_link(db):
    u = _user(db)
    c = _company(db, careers="https://acme.example/careers")
    _vac(db, c, "Has direct link", link="https://acme.example/apply/42")
    _vac(db, c, "No direct link", link=None)
    body = render_digest(u, build_content(db, u, since=NOW - timedelta(hours=24), until=NOW),
                         now=NOW, max_items=25)[1]
    assert "https://acme.example/apply/42" in body
    assert "No direct link" in body and "https://acme.example/careers" in body


def test_preferred_post_type_filters_known_mismatches_only(db):
    u = _user(db, post="internship")
    c = _company(db)
    _vac(db, c, "Engineering Intern", link="https://a.example/1")
    _vac(db, c, "Senior Accountant (Permanent)", link="https://a.example/2")
    _vac(db, c, "Operations Coordinator", link="https://a.example/3")   # no signal: kept
    body = render_digest(u, build_content(db, u, since=NOW - timedelta(hours=24), until=NOW),
                         now=NOW, max_items=25)[1]
    assert "Engineering Intern" in body and "Operations Coordinator" in body
    assert "Senior Accountant" not in body
    none_pref = _user(db, post="none")
    assert build_content(db, none_pref, since=NOW - timedelta(hours=24), until=NOW).total == 0


def test_email_is_capped_at_25_items_with_a_see_more_line(db, monkeypatch):
    u = _user(db)
    c = _company(db)
    for i in range(40):
        _vac(db, c, f"Role {i:02d}", link=f"https://acme.example/apply/{i}")
    subject, body, listed = render_digest(
        u, build_content(db, u, since=NOW - timedelta(hours=24), until=NOW), now=NOW, max_items=25)
    assert listed == 25
    assert body.count("https://acme.example/apply/") == 25
    assert "...and 15 more" in body and "/agent" in body
    assert "40 new for you" in subject


def test_cap_counts_other_mail_sent_in_the_last_24h(db, monkeypatch):
    monkeypatch.setattr(settings, "DIGEST_DAILY_SEND_CAP", 3)
    u1, u2 = _user(db), _user(db)
    for _ in range(3):
        db.add(Notification(user_id=u1.id, type="report_ready", title="t", body="b", email_sent=True,
                            created_at=NOW - timedelta(hours=1)))
    db.commit()
    _vac(db, _company(db), "Role")
    rec = Recorder()
    out = run_daily_digest(db, now=NOW, provider=rec)
    assert out["sent"] == 0 and out["capped"] == 2 and rec.sent == []


def test_a_slow_run_stops_at_its_time_budget_and_the_next_call_finishes(db, monkeypatch):
    for _ in range(2):
        _user(db)
    _vac(db, _company(db), "Role")
    rec = Recorder()
    monkeypatch.setattr("app.services.daily_digest.MAX_RUN_SECONDS", -1.0)
    out = run_daily_digest(db, now=NOW, provider=rec)
    assert out["sent"] == 0 and out["time_limited"] is True
    monkeypatch.undo()
    monkeypatch.setattr(settings, "DIGEST_DAILY_SEND_CAP", 250)
    assert run_daily_digest(db, now=NOW, provider=rec)["sent"] == 2
    assert run_daily_digest(db, now=NOW, provider=rec)["sent"] == 0


def test_default_cap_is_250():
    from app.core.config import Settings
    assert Settings.model_fields["DIGEST_DAILY_SEND_CAP"].default == 250


# ---------------------------------------------------------------- dry run and cron

def test_dry_run_reports_without_sending_or_recording(db):
    _user(db)
    _user(db, alerts=False)
    _vac(db, _company(db), "Role")
    rec = Recorder()
    out = run_daily_digest(db, now=NOW, dry_run=True, provider=rec)
    assert out["dry_run"] is True and out["would_send"] == 1 and out["sent"] == 0
    assert rec.sent == [] and db.query(DigestLog).count() == 0
    assert out["preview"][0]["items"] == 1
    assert "email" not in str(out["preview"]).lower()


def test_cron_endpoint_requires_the_secret_and_honours_dry_run(client, db, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "s3cret")
    ConsoleEmailProvider.outbox.clear()
    assert client.post("/api/v1/cron/run/send_daily_digest").status_code == 401
    monkeypatch.setattr(settings, "DIGEST_DRY_RUN", True)
    now = datetime.now(timezone.utc)
    _user(db)
    c = _company(db)
    v = _vac(db, c, "Role")
    v.first_seen_at = now - timedelta(hours=1)
    db.commit()
    r = client.post("/api/v1/cron/run/send_daily_digest", headers={"X-Cron-Secret": "s3cret"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "success" and '"would_send": 1' in r.json()["detail"]
    assert ConsoleEmailProvider.outbox == [] and db.query(DigestLog).count() == 0


def test_job_is_registered_with_a_0600_utc_schedule():
    from app.scheduler.registry import DEFAULT_SCHEDULE, JOBS
    assert "send_daily_digest" in JOBS
    assert DEFAULT_SCHEDULE["send_daily_digest"] == "0 6 * * *"


# ---------------------------------------------------------------- nothing else mails opportunities

def test_opportunity_notifications_never_email_individually(db, monkeypatch):
    from app.services.notification_service import DIGEST_ONLY_TYPES, create_notification
    monkeypatch.setattr(settings, "NOTIFY_EMAILS", True)
    u = _user(db)
    ConsoleEmailProvider.outbox.clear()
    for t in sorted(DIGEST_ONLY_TYPES):
        n = create_notification(db, user_id=u.id, to_email=u.email, type=t, title=t, body="b",
                                related_id=f"r-{t}", send_email=True)
        assert n is not None and n.email_sent is False
    assert ConsoleEmailProvider.outbox == []


def test_account_mail_stays_immediate(client):
    ConsoleEmailProvider.outbox.clear()
    reg = client.post("/api/v1/auth/register", json={
        "email": "fresh@example.com", "password": "StrongPass123!", "first_name": "F",
        "last_name": "L", "accepted_policy": True})
    assert reg.status_code == 201, reg.text
    client.post("/api/v1/auth/password-reset/request", json={"email": "fresh@example.com"})
    subjects = [m["subject"] for m in ConsoleEmailProvider.outbox]
    assert any(s.startswith("Verify your") for s in subjects)
    assert any(s.startswith("Reset your") for s in subjects)
