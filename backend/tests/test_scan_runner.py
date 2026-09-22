"""Tests for the parallel scanner: selection/back-off, concurrency, deadline, failure handling."""
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.services.scan_runner import (
    backoff_hours, scan_due_parallel, select_due_company_ids, MIN_RESCAN_HOURS,
)
from app.services.scan_service import ScanReport

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _co(db, name, url="https://example.com/careers", country="South Africa", last=None):
    c = Company(company_name=name, careers_url=url, country=country, last_checked=last)
    db.add(c); db.commit(); db.refresh(c)
    return c


def _src(db, company, fails):
    s = VacancySource(company_id=company.id, url=company.careers_url, ats_type="static_html",
                      consecutive_failures=fails)
    db.add(s); db.commit()
    return s


def test_backoff_grows_and_caps():
    assert backoff_hours(0) == MIN_RESCAN_HOURS
    assert backoff_hours(1) == MIN_RESCAN_HOURS      # floor
    assert backoff_hours(5) == 32.0
    assert backoff_hours(50) == 24.0 * 7             # capped at a week


def test_selection_priority_and_backoff(db):
    old = NOW - timedelta(days=3)
    never_other = _co(db, "NeverOther", country="Kenya")
    never_sa = _co(db, "NeverSA")
    never_sa_ats = _co(db, "NeverSAGreenhouse", url="https://boards.greenhouse.io/x")
    fresh = _co(db, "Fresh", last=NOW - timedelta(hours=1))           # too recent
    stale = _co(db, "Stale", last=old)
    dead = _co(db, "Dead", last=NOW - timedelta(hours=48))
    _src(db, dead, fails=8)                                            # backed off ~a week
    ids = select_due_company_ids(db, limit=10, now=NOW)
    assert ids == [never_sa_ats.id, never_sa.id, never_other.id, stale.id]
    assert fresh.id not in ids and dead.id not in ids


def test_selection_respects_limit_and_skips_inactive(db):
    a = _co(db, "A"); b = _co(db, "B")
    b.active = False; db.commit()
    assert select_due_company_ids(db, limit=5, now=NOW) == [a.id]
    _co(db, "C")
    assert len(select_due_company_ids(db, limit=1, now=NOW)) == 1


def _factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


def test_parallel_scan_runs_concurrently_and_stamps(db, db_engine):
    cos = [_co(db, f"Co{i}") for i in range(6)]
    active = {"now": 0, "peak": 0}
    lock = threading.Lock()

    def fake_scan(session, company):
        with lock:
            active["now"] += 1
            active["peak"] = max(active["peak"], active["now"])
        time.sleep(0.15)
        with lock:
            active["now"] -= 1
        return [ScanReport(source_id="s", status="ok", created=2)]

    out = scan_due_parallel(_factory(db_engine), limit=10, max_seconds=30, workers=3,
                            scan_fn=fake_scan, now=NOW)
    assert out["companies_scanned"] == 6 and out["vacancies_created"] == 12
    assert out["sources_failed"] == 0 and out["stopped_early_on_time_budget"] is False
    assert active["peak"] >= 2                      # genuinely concurrent
    for c in cos:
        db.refresh(c)
        assert c.last_checked is not None


def test_one_crashing_company_does_not_stop_the_batch_and_bumps_backoff(db, db_engine):
    good = _co(db, "Good"); bad = _co(db, "Bad")
    _src(db, bad, fails=0)

    def fake_scan(session, company):
        if company.id == bad.id:
            raise RuntimeError("boom")
        return [ScanReport(source_id="s", status="ok", created=1)]

    out = scan_due_parallel(_factory(db_engine), limit=10, max_seconds=30, workers=2,
                            scan_fn=fake_scan, now=NOW)
    assert out["companies_scanned"] == 2 and out["sources_failed"] == 1
    assert out["vacancies_created"] == 1
    db.expire_all()
    assert db.get(Company, bad.id).last_checked is not None
    src = db.query(VacancySource).filter_by(company_id=bad.id).one()
    assert src.consecutive_failures == 1
    assert db.get(Company, good.id).last_checked is not None


def test_deadline_stops_starting_new_scans(db, db_engine):
    for i in range(6):
        _co(db, f"Slow{i}")

    def slow_scan(session, company):
        time.sleep(0.3)
        return [ScanReport(source_id="s", status="ok")]

    out = scan_due_parallel(_factory(db_engine), limit=10, max_seconds=0.2, workers=1,
                            scan_fn=slow_scan, now=NOW)
    assert 1 <= out["companies_scanned"] < 6
    assert out["stopped_early_on_time_budget"] is True
