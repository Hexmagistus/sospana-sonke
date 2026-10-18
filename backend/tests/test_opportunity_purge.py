"""Expired rows are backed up, then deleted, and are not imported again."""
import gzip
import json
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from app.models.admin_ops import AdminAuditLog
from app.models.opportunity_tombstone import OpportunityTombstone
from app.models.organisation import EmployerEntitlement
from app.models.saved_opportunity import SavedOpportunity
from app.models.usage_count import UsageClickDaily
from app.models.vacancy import Vacancy
from app.scheduler.registry import DEFAULT_SCHEDULE, JOBS
from app.services.opportunity_expiry import sa_today
from app.services.opportunity_purge import purge_expired_opportunities
from app.services.opportunity_tombstone import identity_hashes, listing_was_deleted
from app.services.storage import get_storage
from tests.test_expired_opportunities import _auth, _seed
from tests.conftest import make_admin, register_and_login


def test_board_url_is_not_stored_as_the_role_identity():
    hashes = identity_hashes(
        company_id="company",
        external_id=None,
        source_url="https://board.example/careers",
        canonical_url="https://board.example/careers",
        application_url="https://board.example/careers",
        fingerprint="abc123",
        board_url="https://board.example/careers",
    )
    assert len(hashes) == 1


def test_purge_backs_up_then_deletes_and_blocks_reimport(client, db_engine, monkeypatch):
    ids = _seed(db_engine)
    register_and_login(client)
    session = sessionmaker(bind=db_engine)()
    today = sa_today()
    dated = session.get(Vacancy, ids["dated_id"])
    gone = session.get(Vacancy, ids["gone_id"])
    dated.external_id = "req-dated"
    dated.application_url = "https://ward.example/jobs/dated"
    dated.source_url = "https://ward.example/jobs/dated"
    gone.external_id = "req-gone"
    gone.application_url = "https://ward.example/jobs/gone"
    session.add(UsageClickDaily(day=today, target_kind="vacancy", target_id=dated.id, clicks=4))
    session.commit()
    session.close()

    seen = []
    real = get_storage()
    check = sessionmaker(bind=db_engine)

    class _Recording:
        def put(self, key, data):
            probe = check()
            try:
                seen.append(probe.query(Vacancy).count())
            finally:
                probe.close()
            return real.put(key, data)

        def get(self, key):
            probe = check()
            try:
                seen.append(probe.query(Vacancy).count())
            finally:
                probe.close()
            return real.get(key)

    monkeypatch.setattr("app.services.opportunity_purge.get_storage", lambda: _Recording())
    session = sessionmaker(bind=db_engine)()
    try:
        result = purge_expired_opportunities(session)
    finally:
        session.close()

    assert seen == [3, 3]
    assert result["deleted"] == 2
    assert result["bookmarks"] == 0
    assert result["clicks"] == 1
    assert result["featured_ended"] == 1
    assert result["backup"].startswith("private/expired-opportunities/")
    assert result["backup"].endswith(".json.gz")

    body = json.loads(gzip.decompress(get_storage().get(result["backup"])))
    titles = {row["title"] for row in body["vacancies"]}
    assert titles == {"Expired Nurse", "Gone Nurse"}
    assert body["bookmarks"] == []
    assert body["clicks"][0]["clicks"] == 4
    assert body["featured"][0]["status"] == "active"

    session = sessionmaker(bind=db_engine)()
    try:
        assert session.get(Vacancy, ids["dated_id"]) is None
        assert session.get(Vacancy, ids["gone_id"]) is None
        assert session.get(Vacancy, ids["live_id"]) is not None
        assert session.query(SavedOpportunity).count() == 0
        assert session.query(UsageClickDaily).count() == 0
        featured = session.query(EmployerEntitlement).one()
        assert featured.status == "expired"
        columns = {col["name"] for col in inspect(db_engine).get_columns("opportunity_tombstones")}
        assert columns == {"key_hash", "deleted_at"}
        tombstone = session.query(OpportunityTombstone).first()
        assert tombstone is not None
        assert not hasattr(tombstone, "title")
        assert listing_was_deleted(
            session,
            company_id=ids["company_id"],
            external_id="req-dated",
            source_url="https://ward.example/jobs/dated",
            canonical_url=None,
            application_url="https://ward.example/jobs/dated",
            fingerprint=None,
            board_url="https://ward.example/careers",
        )
        assert listing_was_deleted(
            session,
            company_id=ids["company_id"],
            external_id="req-new",
            source_url=None,
            canonical_url=None,
            application_url=None,
            fingerprint=None,
            board_url="https://ward.example/careers",
        ) is False
        audit = session.query(AdminAuditLog).filter(AdminAuditLog.action == "purge_expired").one()
        assert "deleted=2" in audit.detail
        assert result["backup"] in audit.detail
        again = purge_expired_opportunities(session)
        assert again["deleted"] == 0
        assert again["backup"] is None
    finally:
        session.close()

    listed = client.get("/api/v1/jobs", params={"q": "Nurse"}).json()["jobs"]
    assert {row["id"] for row in listed} == {ids["live_id"]}
    sitemap = client.get("/api/v1/jobs/ids").json()["ids"]
    assert ids["dated_id"] not in sitemap
    assert ids["live_id"] in sitemap
    closed = client.get(f"/api/v1/jobs/{ids['dated_id']}")
    assert closed.status_code == 410
    assert closed.json()["detail"] == "This opportunity has closed."
    assert "noindex" in closed.headers.get("x-robots-tag", "")
    assert client.get("/api/v1/jobs/does-not-exist").status_code == 404
    assert client.get(f"/api/v1/jobs/{ids['live_id']}").status_code == 200

    _, tokens = register_and_login(client, email="reader2@example.com")
    hidden = client.get(f"/api/v1/vacancies/{ids['gone_id']}", headers=_auth(tokens))
    assert hidden.status_code == 410

    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    payload = client.get("/api/v1/admin/vacancies", params={"status": "expired"}, headers=_auth(admin)).json()
    assert payload["expired"] == 0
    assert payload["active"] == 1
    assert payload["rows"] == []
    active = client.get("/api/v1/admin/vacancies", params={"status": "active"}, headers=_auth(admin)).json()
    assert [row["id"] for row in active["rows"]] == [ids["live_id"]]


def test_failed_backup_deletes_nothing(client, db_engine, monkeypatch):
    ids = _seed(db_engine)

    class _Boom:
        def put(self, key, data):
            raise RuntimeError("backup failed")

        def get(self, key):
            raise FileNotFoundError(key)

    monkeypatch.setattr("app.services.opportunity_purge.get_storage", lambda: _Boom())
    session = sessionmaker(bind=db_engine)()
    try:
        with pytest.raises(RuntimeError, match="backup failed"):
            purge_expired_opportunities(session)
        session.rollback()
        assert session.get(Vacancy, ids["dated_id"]).title == "Expired Nurse"
        assert session.get(Vacancy, ids["gone_id"]) is not None
        assert session.query(OpportunityTombstone).count() == 0
        assert session.query(AdminAuditLog).count() == 0
    finally:
        session.close()


def test_purge_job_is_scheduled():
    assert "purge_expired_opportunities" in JOBS
    assert DEFAULT_SCHEDULE["purge_expired_opportunities"] == "30 1 * * *"
    workflow = Path(__file__).resolve().parents[2].joinpath(".github/workflows/scan.yml").read_text()
    assert "purge_expired_opportunities" in workflow


@pytest.fixture(autouse=True)
def _purge_switched_on(monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_PURGE_ENABLED", "true")
