"""Listings in one batch that share an address or fingerprint, or whose
tombstone already exists, must not stop the purge with a duplicate key."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.models.opportunity_tombstone import OpportunityTombstone
from app.models.stored_file import StoredFile  # noqa: F401
from app.models.vacancy import Vacancy
from app.services.opportunity_expiry import sa_today
from app.services.opportunity_purge import purge_expired_opportunities
from app.services.opportunity_tombstone import listing_was_deleted, public_id_hash, url_hash
from app.services.storage import get_storage
from tests.test_expired_opportunities import _seed

SHARED_PAGE = "https://ward.example/jobs"  # a general page many roles link to


@pytest.fixture(autouse=True)
def _purge_on(monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_PURGE_ENABLED", "true")
    monkeypatch.delenv("OPPORTUNITY_PURGE_BATCH", raising=False)


def _expired(session, ids, title, **fields):
    now = datetime.now(timezone.utc)
    base = session.get(Vacancy, ids["dated_id"])
    row = Vacancy(
        company_id=ids["company_id"], source_id=base.source_id, title=title,
        content_hash=title, is_open=False, status="active", lifecycle_status="CLOSED",
        closing_date=sa_today(now) - timedelta(days=3), country="South Africa",
        first_seen_at=now, last_seen_at=now, opportunity_type="job", **fields,
    )
    session.add(row)
    return row


def test_colliding_listings_are_purged_with_one_tombstone_each(db_engine):
    ids = _seed(db_engine)
    session = sessionmaker(bind=db_engine)()
    rows = [
        _expired(session, ids, f"Shared page role {n}", external_id=f"req-{n}", application_url=SHARED_PAGE)
        for n in range(3)
    ]
    # Two copies of the same role: same own address and same fingerprint.
    twin_a = _expired(session, ids, "Twin A", source_url="https://ward.example/jobs/42", fingerprint="fp-42")
    twin_b = _expired(session, ids, "Twin B", source_url="https://ward.example/jobs/42", fingerprint="fp-42")
    session.commit()
    expired_ids = [row.id for row in rows] + [twin_a.id, twin_b.id]
    company_id = ids["company_id"]
    # A tombstone from an earlier run already holds one of the hashes.
    session.add(OpportunityTombstone(key_hash=public_id_hash(rows[0].id), deleted_at=datetime.now(timezone.utc)))
    session.commit()
    session.close()

    session = sessionmaker(bind=db_engine)()
    try:
        result = purge_expired_opportunities(session)
    finally:
        session.close()

    assert result["deleted"] == 2 + len(expired_ids)  # the seeded dated and gone rows too
    session = sessionmaker(bind=db_engine)()
    try:
        for vacancy_id in expired_ids:
            assert session.get(Vacancy, vacancy_id) is None
            assert session.get(OpportunityTombstone, public_id_hash(vacancy_id)) is not None
        assert session.get(Vacancy, ids["live_id"]) is not None
        hashes = [row[0] for row in session.query(OpportunityTombstone.key_hash).all()]
        assert len(hashes) == len(set(hashes))
        # The shared page is not stored as any one role's address, so a new
        # role that links to it is still imported.
        assert session.get(OpportunityTombstone, url_hash(company_id, SHARED_PAGE)) is None
        assert not listing_was_deleted(
            session, company_id=company_id, external_id="req-new", source_url=None,
            canonical_url=None, application_url=SHARED_PAGE, fingerprint=None,
            board_url="https://ward.example/careers",
        )
        # Each role's own reference still blocks it from coming back.
        assert listing_was_deleted(
            session, company_id=company_id, external_id="req-1", source_url=None,
            canonical_url=None, application_url=SHARED_PAGE, fingerprint=None,
            board_url="https://ward.example/careers",
        )
        # The twins share a fingerprint: it is stored once and still blocks
        # the role from coming back.
        assert listing_was_deleted(
            session, company_id=company_id, external_id=None, source_url="https://ward.example/jobs/42",
            canonical_url=None, application_url=None, fingerprint="fp-42",
            board_url="https://ward.example/careers",
        )
        # One new tombstone for each hash the run inserted; the existing one is not counted.
        assert result["tombstones"] == len(hashes) - 1
    finally:
        session.close()


def test_a_run_after_a_rolled_back_run_uses_a_new_backup_key(db_engine):
    _seed(db_engine)
    # Pinned to the current second: the seeded rows are dated from today.
    when = datetime.now(timezone.utc).replace(microsecond=0)
    # The rolled-back run left its backup behind under the old key format.
    leftover = f"private/expired-opportunities/{when:%Y%m%dT%H%M%SZ}-2.json.gz"
    get_storage().put(leftover, b"left over")
    session = sessionmaker(bind=db_engine)()
    try:
        first = purge_expired_opportunities(session, when=when)
    finally:
        session.close()
    assert first["deleted"] == 2
    assert first["backup"] != leftover
    assert get_storage().get(leftover) == b"left over"

    ids = _seed(db_engine)
    session = sessionmaker(bind=db_engine)()
    try:
        second = purge_expired_opportunities(session, when=when)  # same second, same count
    finally:
        session.close()
    assert second["deleted"] == 2
    assert second["backup"] != first["backup"]
    assert get_storage().get(first["backup"]) != get_storage().get(second["backup"])
    assert ids
