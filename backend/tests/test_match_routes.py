"""Matching has been removed: every old route answers 410, nothing is computed or stored,
and the retired cron jobs answer with a harmless "disabled" result."""
import json

import pytest

from tests.conftest import register_and_login
from app.models.match import CandidateMatch
from app.scheduler.runner import run_job
from app.services import match_service


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


OLD_ROUTES = [
    ("post", "/api/v1/matches/run"),
    ("get", "/api/v1/matches"),
    ("get", "/api/v1/matches/abc"),
    ("get", "/api/v1/matches/abc/gap-analysis"),
    ("post", "/api/v1/matches/abc/gap-analysis"),
    ("get", "/api/v1/matches/abc/interview-prep"),
    ("post", "/api/v1/matches/abc/interview-prep"),
    ("post", "/api/v1/matches/abc/generate-cv"),
    ("post", "/api/v1/matches/abc/generate-cover-letter"),
    ("post", "/api/v1/matches/abc/prepare-application"),
    ("get", "/api/v1/admin/match-config"),
    ("put", "/api/v1/admin/match-config"),
]


@pytest.mark.parametrize("method,path", OLD_ROUTES)
def test_old_match_routes_return_410(client, method, path):
    _, tokens = register_and_login(client)
    r = getattr(client, method)(path, headers=_auth(tokens))
    assert r.status_code == 410, r.text
    assert "removed" in r.json()["detail"].lower()


def test_old_match_routes_410_even_when_logged_out(client):
    # a stale tab / bookmark must see "gone", not 401/403/500
    assert client.post("/api/v1/matches/run").status_code == 410
    assert client.get("/api/v1/matches").status_code == 410


def test_running_matching_stores_nothing(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    _, tokens = register_and_login(client)
    client.post("/api/v1/matches/run", headers=_auth(tokens))
    db = sessionmaker(bind=db_engine)()
    try:
        assert db.query(CandidateMatch).count() == 0
    finally:
        db.close()


def test_match_service_no_longer_has_a_runner():
    assert not hasattr(match_service, "run_match_for_user")


@pytest.mark.parametrize("name", ["match_all_candidates", "run_daily_agent"])
def test_retired_jobs_return_disabled_not_error(db_engine, name):
    from sqlalchemy.orm import sessionmaker
    db = sessionmaker(bind=db_engine)()
    try:
        run = run_job(db, name)
        assert run.status == "success"
        assert json.loads(run.detail)["status"] == "disabled"
    finally:
        db.close()


def test_retired_job_is_not_scheduled_by_default():
    from app.scheduler.registry import DEFAULT_SCHEDULE, JOBS
    assert "match_all_candidates" in JOBS          # still callable by name (cron-job.org)
    assert "match_all_candidates" not in DEFAULT_SCHEDULE
