"""Tests for the proactive Daily Agent (app/services/agent_service.py).

Covers the core promise behind the feature: it drafts a CV + cover letter and
queues a ready-to-review application for a candidate's strongest new match,
never creates a second application for the same vacancy, respects the
candidate's own daily cap, and never leaves an application anywhere but an
approval-required status (i.e. it never submits anything itself).
"""
from sqlalchemy.orm import sessionmaker

from tests.conftest import register_and_login
from tests.test_applications import _auth, _enrich, _seed_vacancy

from app.models.application import Application
from app.models.document import CVVersion, CoverLetter
from app.models.notification import Notification
from app.models.user import User
from app.services import agent_service


def _me_id(client, tokens):
    return client.get("/api/v1/auth/me", headers=_auth(tokens)).json()["id"]


def test_daily_agent_drafts_and_queues_for_strong_match(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine, title="Operations Manager", exp="5")
    user_id = _me_id(client, tokens)

    S = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db = S()
    try:
        user = db.get(User, user_id)
        summary = agent_service.run_daily_agent_for_user(db, user, max_new=3)

        assert summary.applications_prepared == 1
        assert summary.cvs_generated == 1
        assert summary.cover_letters_generated == 1
        assert len(summary.applications_ready) == 1

        app = db.get(Application, summary.applications_ready[0])
        # Never auto-submitted: approval mode (the default) lands in
        # AWAITING_APPROVAL, which still requires the candidate to approve
        # AND then submit -- the agent never moves it further than this.
        assert app.status == "AWAITING_APPROVAL"
        assert app.cv_version_id is not None
        assert app.cover_letter_id is not None
        assert db.query(CVVersion).filter(CVVersion.user_id == user.id).count() == 1
        assert db.query(CoverLetter).filter(CoverLetter.user_id == user.id).count() == 1

        note = (db.query(Notification)
                .filter(Notification.user_id == user.id, Notification.type == "daily_agent_briefing")
                .first())
        assert note is not None
        assert "Operations Manager" in note.body
    finally:
        db.close()


def test_daily_agent_never_duplicates_an_application(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine, title="Operations Manager", exp="5")
    user_id = _me_id(client, tokens)

    S = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db = S()
    try:
        user = db.get(User, user_id)
        first = agent_service.run_daily_agent_for_user(db, user, max_new=3)
        assert first.applications_prepared == 1

        second = agent_service.run_daily_agent_for_user(db, user, max_new=3)
        assert second.applications_prepared == 0
        assert db.query(Application).filter(Application.user_id == user.id).count() == 1
    finally:
        db.close()


def test_daily_agent_respects_the_daily_cap(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine, title="Operations Manager", exp="5")
    _seed_vacancy(db_engine, title="Operations Team Lead", exp="4")
    user_id = _me_id(client, tokens)

    client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "approval", "auto_apply_enabled": False, "min_match_score": 0,
        "max_applications_per_day": 0, "max_applications_per_week": 25,
        "excluded_companies": [], "excluded_roles": [],
    })

    S = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db = S()
    try:
        user = db.get(User, user_id)
        summary = agent_service.run_daily_agent_for_user(db, user, max_new=3)
        assert summary.applications_prepared == 0
        assert summary.skipped >= 1
        assert db.query(Application).filter(Application.user_id == user.id).count() == 0
    finally:
        db.close()


def test_run_daily_agent_across_all_candidates(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _enrich(client, tokens_a)
    user_a_id = _me_id(client, tokens_a)
    _, tokens_b = register_and_login(client, email="b@example.com")
    _enrich(client, tokens_b)
    user_b_id = _me_id(client, tokens_b)
    _seed_vacancy(db_engine, title="Operations Manager", exp="5")

    S = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db = S()
    try:
        result = agent_service.run_daily_agent(db, job_run_id="test-run-1", max_new_per_user=3)
        assert result["candidates_processed"] == 2
        assert result["candidates_with_new_applications"] == 2
        assert result["applications_prepared"] == 2

        # Re-running the same job_run_id must not double-notify either candidate.
        agent_service.run_daily_agent(db, job_run_id="test-run-1", max_new_per_user=3)
        for uid in (user_a_id, user_b_id):
            count = (db.query(Notification)
                     .filter(Notification.user_id == uid,
                             Notification.type == "daily_agent_briefing").count())
            assert count == 1
    finally:
        db.close()


def test_cron_endpoint_can_trigger_the_daily_agent(client, db_engine, monkeypatch):
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "CRON_SECRET", "test-cron-secret")

    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    _seed_vacancy(db_engine, title="Operations Manager", exp="5")
    user_id = _me_id(client, tokens)

    r = client.post("/api/v1/cron/run/run_daily_agent", headers={"X-Cron-Secret": "test-cron-secret"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"

    S = sessionmaker(bind=db_engine)
    db = S()
    try:
        assert db.query(Application).filter(Application.user_id == user_id).count() == 1
    finally:
        db.close()
