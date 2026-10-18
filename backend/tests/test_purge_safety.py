"""The purge never touches users' applications or bookmarks, backs up every row
it changes, and works in small batches."""
import gzip
import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (register every table on the metadata)
from app.db.base import Base
from app.models.application import Application, ApplicationAnswer, ApplicationEvent
from app.models.match import CandidateMatch
from app.models.saved_opportunity import SavedOpportunity
from app.models.vacancy import Vacancy
from app.services import opportunity_purge
from app.services.opportunity_purge import (
    BACKED_UP_TABLES, DEFAULT_BATCH, MAX_BATCH, batch_size, purge_expired_opportunities,
)
from app.services.storage import get_storage
from tests.test_expired_opportunities import _seed

# Tables the purge deletes rows from. A foreign key that reaches one of them
# with CASCADE or SET NULL changes rows in the referencing table too.
_DELETED = {"vacancies", "candidate_matches", "vacancy_requirements", "vacancy_reports", "usage_click_daily"}


@pytest.fixture(autouse=True)
def _purge_switched_on(monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_PURGE_ENABLED", "true")
    monkeypatch.delenv("OPPORTUNITY_PURGE_BATCH", raising=False)


def _archive(key):
    return json.loads(gzip.decompress(get_storage().get(key)))


def test_every_table_a_delete_can_reach_is_backed_up():
    """Fails when a new foreign key lets the purge change a table it does not archive."""
    reached = set(_DELETED)
    grew = True
    while grew:
        grew = False
        for table in Base.metadata.sorted_tables:
            for fk in table.foreign_keys:
                if fk.column.table.name in reached and (fk.ondelete or "").upper() in ("CASCADE", "SET NULL"):
                    if fk.ondelete.upper() == "CASCADE" and table.name not in reached:
                        reached.add(table.name)
                        grew = True
                    missing = table.name not in BACKED_UP_TABLES
                    assert not missing, (
                        f"{table.name}.{fk.parent.name} -> {fk.column.table.name} ({fk.ondelete}) "
                        "is not backed up by the purge"
                    )
    # Plain references without a foreign key are archived too.
    for name in ("usage_click_daily", "employer_entitlements", "employer_opportunities"):
        assert name in BACKED_UP_TABLES


def test_every_backed_up_table_is_written_to_the_archive():
    archived = {"vacancies"} | {model.__tablename__ for _n, model, *_r in opportunity_purge._sections()}
    assert BACKED_UP_TABLES <= archived


def test_applied_and_bookmarked_listings_are_never_deleted(db_engine):
    ids = _seed(db_engine)
    s = sessionmaker(bind=db_engine)()
    try:
        app_row = Application(user_id="u1", vacancy_id=ids["dated_id"], mode="approval", status="AWAITING_APPROVAL")
        s.add(app_row)
        s.commit()
        s.add(ApplicationAnswer(application_id=app_row.id, question="Why?", answer="Because."))
        s.add(ApplicationEvent(application_id=app_row.id, event_type="created"))
        s.add(SavedOpportunity(user_id="u2", vacancy_id=ids["gone_id"]))
        s.commit()
    finally:
        s.close()

    s = sessionmaker(bind=db_engine)()
    try:
        result = purge_expired_opportunities(s)
        assert result["deleted"] == 0
        assert result["backup"] is None
        assert result["due"] == 0
        assert result["kept_for_users"] == 2
        assert s.get(Vacancy, ids["dated_id"]) is not None
        assert s.get(Vacancy, ids["gone_id"]) is not None
        assert s.query(Application).count() == 1
        assert s.query(ApplicationAnswer).count() == 1
        assert s.query(ApplicationEvent).count() == 1
        assert s.query(SavedOpportunity).count() == 1
    finally:
        s.close()


def test_guard_stops_before_any_change_if_an_applied_listing_slips_in(db_engine):
    ids = _seed(db_engine)
    s = sessionmaker(bind=db_engine)()
    try:
        s.add(Application(user_id="u1", vacancy_id=ids["gone_id"], mode="approval", status="AWAITING_APPROVAL"))
        s.commit()
        with pytest.raises(RuntimeError, match="application"):
            opportunity_purge._delete(s, [ids["dated_id"], ids["gone_id"]], datetime.now(timezone.utc))
        s.rollback()
        assert s.get(Vacancy, ids["dated_id"]) is not None
        assert s.get(Vacancy, ids["gone_id"]) is not None
        assert s.query(Application).count() == 1
    finally:
        s.close()


def test_matches_and_cleared_links_are_in_the_backup(db_engine):
    ids = _seed(db_engine)
    s = sessionmaker(bind=db_engine)()
    try:
        match = CandidateMatch(user_id="u1", vacancy_id=ids["gone_id"], score=70.0)
        s.add(match)
        s.commit()
        # An application on the live role that points at the gone role's match.
        other = Application(user_id="u1", vacancy_id=ids["live_id"], match_id=match.id,
                            mode="approval", status="AWAITING_APPROVAL")
        s.add(other)
        s.commit()
        match_id, other_id = match.id, other.id
    finally:
        s.close()

    s = sessionmaker(bind=db_engine)()
    try:
        result = purge_expired_opportunities(s)
        assert result["deleted"] == 2
        assert result["matches_backed_up"] == 1
        body = _archive(result["backup"])
        assert [row["id"] for row in body["matches"]] == [match_id]
        assert [(row["id"], row["match_id"]) for row in body["applications"]] == [(other_id, match_id)]
        assert body["application_answers"] == [] and body["application_events"] == []
        assert s.query(CandidateMatch).count() == 0
        kept = s.get(Application, other_id)
        assert kept is not None and kept.match_id is None
        assert s.get(Vacancy, ids["live_id"]) is not None
    finally:
        s.close()


def test_one_run_deletes_at_most_one_batch(db_engine, monkeypatch):
    ids = _seed(db_engine)
    s = sessionmaker(bind=db_engine)()
    now = datetime.now(timezone.utc)
    try:
        for n in range(5):
            s.add(Vacancy(
                company_id=ids["company_id"], source_id="src", title=f"Old Role {n}",
                content_hash=f"old-{n}", is_open=False, status="expired", lifecycle_status="EXPIRED",
                first_seen_at=now - timedelta(days=30), last_seen_at=now - timedelta(days=30),
            ))
        s.commit()
    finally:
        s.close()
    monkeypatch.setenv("OPPORTUNITY_PURGE_BATCH", "3")
    s = sessionmaker(bind=db_engine)()
    try:
        first = purge_expired_opportunities(s)
        assert first["batch_limit"] == 3
        assert first["deleted"] == 3
        assert first["remaining"] == 4
        assert len(_archive(first["backup"])["vacancies"]) == 3
        second = purge_expired_opportunities(s, when=datetime.now(timezone.utc) + timedelta(seconds=1))
        assert second["deleted"] == 3 and second["remaining"] == 1
        third = purge_expired_opportunities(s, when=datetime.now(timezone.utc) + timedelta(seconds=2))
        assert third["deleted"] == 1 and third["remaining"] == 0
        assert s.query(Vacancy).count() == 1  # only the live role
    finally:
        s.close()


def test_batch_size_defaults_and_limits(monkeypatch):
    monkeypatch.delenv("OPPORTUNITY_PURGE_BATCH", raising=False)
    assert batch_size() == DEFAULT_BATCH == 1000
    monkeypatch.setenv("OPPORTUNITY_PURGE_BATCH", "999999")
    assert batch_size() == MAX_BATCH
    monkeypatch.setenv("OPPORTUNITY_PURGE_BATCH", "0")
    assert batch_size() == 1
    monkeypatch.setenv("OPPORTUNITY_PURGE_BATCH", "lots")
    assert batch_size() == DEFAULT_BATCH


def test_switched_off_does_nothing(db_engine, monkeypatch):
    ids = _seed(db_engine)
    monkeypatch.setenv("OPPORTUNITY_PURGE_ENABLED", "false")
    s = sessionmaker(bind=db_engine)()
    try:
        assert purge_expired_opportunities(s)["disabled"] is True
        assert s.get(Vacancy, ids["gone_id"]) is not None
    finally:
        s.close()


def test_a_full_batch_stays_small_in_memory(db_engine):
    """1,000 listings with long descriptions must back up and delete well inside 512 MB."""
    import tracemalloc

    ids = _seed(db_engine)
    s = sessionmaker(bind=db_engine)()
    now = datetime.now(timezone.utc)
    text = "Duties include patient care, records and ward rounds. " * 80  # about 4 KB
    try:
        s.add_all([
            Vacancy(
                company_id=ids["company_id"], source_id="src", title=f"Old Role {n}",
                content_hash=f"bulk-{n}", is_open=False, status="expired", lifecycle_status="REMOVED",
                description=text, first_seen_at=now, last_seen_at=now,
            )
            for n in range(1000)
        ])
        s.commit()
    finally:
        s.close()
    s = sessionmaker(bind=db_engine)()
    tracemalloc.start()
    try:
        result = purge_expired_opportunities(s)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        s.close()
    assert result["deleted"] == 1000
    assert result["remaining"] == 2
    assert peak < 120 * 1024 * 1024, f"peak {peak / 1e6:.0f} MB"
