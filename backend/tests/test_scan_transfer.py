"""Rescans that change nothing do not read full vacancy rows back.

The Neon free plan caps monthly network transfer. These tests pin the cheap
paths: an unchanged listing is stamped with one UPDATE, a changed one still
gets the full update, and the due queue is built once and handed out in slices.
"""
import re
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import event

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.scraper.base import RawVacancy
from app.services import scan_runner
from app.services.scan_service import FetchOutcome, apply_fetch

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def _source(db):
    company = Company(
        company_name="Transfer Test Ltd", country="South Africa", source_type="PRIVATE",
        careers_url="https://transfer.example/careers", active=True,
    )
    db.add(company)
    db.commit()
    source = VacancySource(
        company_id=company.id, url="https://transfer.example/careers", ats_type="static", active=True,
    )
    db.add(source)
    db.commit()
    return company, source


def _scan(db, source, description="Run the plant. Matric required.", when=NOW):
    outcome = FetchOutcome(
        kind="ok", started=time.monotonic(), now=when, ats_type="static", parser_used="static",
        raw_list=[RawVacancy(
            title="Process Controller", external_id="PC-1", location="Vereeniging",
            description=description, application_url="https://transfer.example/apply/pc-1",
        )],
    )
    return apply_fetch(db, source, outcome)


def _selected_description(db, fn):
    """Run fn and report whether any SELECT read vacancies.description."""
    seen = []

    def before(conn, cursor, statement, params, context, executemany):
        text = statement.lower().lstrip()
        if text.startswith("select"):
            columns = re.split(r"\sfrom\s", text, maxsplit=1)[0]
            if "vacancies.description" in columns:
                seen.append(statement)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", before)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return result, seen


def test_unchanged_rescan_touches_last_seen_without_reading_the_row(db):
    _, source = _source(db)
    first = _scan(db, source)
    assert first.created == 1
    row = db.query(Vacancy).one()
    assert row.is_open and row.status == "active"

    later = NOW + timedelta(hours=1)
    report, reads = _selected_description(db, lambda: _scan(db, source, when=later))
    assert report.updated == 1 and report.created == 0
    assert reads == []

    db.expire_all()
    row = db.query(Vacancy).one()
    assert row.last_seen_at.replace(tzinfo=timezone.utc) == later
    assert row.consecutive_misses == 0
    assert row.is_open is True


def test_changed_description_still_gets_the_full_update(db):
    _, source = _source(db)
    _scan(db, source)
    report = _scan(db, source, description="New wording. Grade 12 and N3 required.",
                   when=NOW + timedelta(hours=1))
    assert report.updated == 1 and report.created == 0
    db.expire_all()
    row = db.query(Vacancy).one()
    assert "New wording" in row.description


def test_closed_row_seen_again_takes_the_full_path(db):
    _, source = _source(db)
    _scan(db, source)
    row = db.query(Vacancy).one()
    row.quality_flags = ["manual_close"]
    db.commit()
    _scan(db, source, when=NOW + timedelta(hours=1))
    db.expire_all()
    row = db.query(Vacancy).one()
    assert row.is_open is False
    assert row.lifecycle_status == "REMOVED"


def test_due_queue_is_built_once_and_handed_out_in_slices(db, monkeypatch):
    calls = []
    items = [scan_runner.DueItem(company_id=f"c{i}", source_id=None, last_scanned=None,
                                 band=0, url=f"https://x{i}.example") for i in range(10)]

    def fake_select_due(_db, limit, now=None):
        calls.append(limit)
        return items[:limit]

    monkeypatch.setattr(scan_runner, "select_due", fake_select_due)
    scan_runner.invalidate_due_cache()
    try:
        first = scan_runner.select_due_cached(db, 2)
        second = scan_runner.select_due_cached(db, 2)
        assert [i.company_id for i in first] == ["c0", "c1"]
        assert [i.company_id for i in second] == ["c2", "c3"]
        assert calls == [8]
        scan_runner.select_due_cached(db, 2)
        scan_runner.select_due_cached(db, 2)
        scan_runner.select_due_cached(db, 2)  # used up: rebuilt
        assert calls == [8, 8]
        scan_runner._due_cache["at"] -= scan_runner.DUE_CACHE_TTL_SECONDS + 1
        scan_runner.select_due_cached(db, 2)  # expired: rebuilt
        assert calls == [8, 8, 8]
    finally:
        scan_runner.invalidate_due_cache()


def test_link_check_job_is_registered_for_the_scan_workflow():
    from pathlib import Path

    from app.scheduler.registry import DEFAULT_SCHEDULE, JOBS

    assert "check_listing_links" in JOBS
    assert DEFAULT_SCHEDULE["review_listing_quality"] == "15 1 * * *"
    root = Path(__file__).resolve().parents[2] / ".github" / "workflows"
    scan = (root / "scan.yml").read_text()
    daily = (root / "daily-agent.yml").read_text()
    assert "check_listing_links" in scan
    assert "review_listing_quality" not in scan
    assert "review_listing_quality" in daily
