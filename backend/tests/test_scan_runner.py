"""Tests for the parallel scanner: selection/back-off, concurrency, deadline, failure handling."""
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.services.scan_runner import (
    FAST_RESCAN_HOURS, backoff_hours, due_after_hours, scan_due_parallel,
    select_due_company_ids, MIN_RESCAN_HOURS,
)
from app.services.scan_service import ScanReport

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _co(db, name, url="https://example.com/careers", country="South Africa", last=None,
        fails=None, success_at=None):
    """A company; with ``last`` (or ``fails``) also its source, scanned at ``last``.

    The queue reads the source's last_checked: the company's own timestamp is
    also stamped by the URL health check and does not mean "scanned".
    """
    c = Company(company_name=name, careers_url=url, country=country, last_checked=last)
    db.add(c); db.commit(); db.refresh(c)
    if last is not None or fails is not None:
        db.add(VacancySource(company_id=c.id, url=url, ats_type="static_html",
                             consecutive_failures=fails or 0, last_checked=last,
                             last_success_at=success_at))
        db.commit()
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
    never_other = _co(db, "NeverOther", country="Kenya")
    never_sa = _co(db, "NeverSA")
    never_sa_ats = _co(db, "NeverSAGreenhouse", url="https://boards.greenhouse.io/x")
    fresh = _co(db, "Fresh", last=NOW - timedelta(hours=1))           # too recent
    stale = _co(db, "Stale", last=NOW - timedelta(days=3))
    dead = _co(db, "Dead", last=NOW - timedelta(hours=48), fails=8)   # backed off a week
    ids = select_due_company_ids(db, limit=10, now=NOW)
    # Never scanned first: South Africa (supported board before plain HTML),
    # then Kenya. Then the oldest scan.
    assert ids == [never_sa_ats.id, never_sa.id, never_other.id, stale.id]
    assert fresh.id not in ids and dead.id not in ids
    assert select_due_company_ids(db, limit=10, now=NOW) == ids


def test_queue_uses_the_source_scan_not_the_url_check(db):
    """test_all_urls stamps Company.last_checked daily; that is not a scan."""
    pinged = Company(company_name="Pinged", careers_url="https://example.com/a",
                     country="South Africa", last_checked=NOW - timedelta(minutes=5))
    db.add(pinged); db.commit()
    ids = select_due_company_ids(db, limit=10, now=NOW)
    assert ids == [pinged.id]


def test_fast_json_boards_are_due_again_after_an_hour(db):
    from app.services.scan_runner import FAST_RESCAN_HOURS
    recent = NOW - timedelta(hours=FAST_RESCAN_HOURS + 0.5)
    html = _co(db, "HtmlRecent", last=recent)
    board = _co(db, "GreenhouseRecent", url="https://boards.greenhouse.io/acme", last=recent)
    ids = select_due_company_ids(db, limit=10, now=NOW)
    assert board.id in ids
    assert html.id not in ids


def test_cihr_boards_rescan_hourly():
    url = "https://atns.ci.hr/applicant/index.php?controller=Page&name=jobsearch"
    assert due_after_hours(url, 0, 0) == FAST_RESCAN_HOURS


def test_empty_boards_are_scanned_less_often(db):
    from app.services.scan_runner import due_after_hours
    quiet = _co(db, "QuietHtml", last=NOW - timedelta(hours=13))
    src = db.query(VacancySource).filter_by(company_id=quiet.id).one()
    src.empty_streak = 3
    db.commit()
    busy = _co(db, "BusyHtml", last=NOW - timedelta(hours=7))
    assert due_after_hours("https://example.com/careers", 0, 0) == MIN_RESCAN_HOURS
    assert due_after_hours("https://example.com/careers", 0, 1) == 12
    assert due_after_hours("https://boards.greenhouse.io/acme", 0, 3) == 24
    assert due_after_hours("https://example.com/careers", 0, 8) == 24 * 7
    ids = select_due_company_ids(db, limit=10, now=NOW)
    assert quiet.id not in ids
    assert busy.id in ids


def test_never_scanned_by_region_then_oldest_with_a_bounded_region_lead(db):
    """Standing order. Never-scanned sources (by region) come first; after that
    the oldest scan wins, with South Africa 36 h, SADC 24 h, Africa 12 h and an
    unparsed supported board another 24 h ahead."""
    australia = _co(db, "Telstra", url="https://boards.greenhouse.io/telstra", country="Australia")
    nigeria = _co(db, "Dangote", url="https://boards.greenhouse.io/dangote", country="Nigeria")
    botswana = _co(db, "Debswana", url="https://boards.greenhouse.io/debswana", country="Botswana")
    older = _co(db, "OlderBoard", url="https://boards.greenhouse.io/older",
                last=NOW - timedelta(days=4))                    # 4d + 36h + 24h
    newer = _co(db, "NewerBoard", url="https://jobs.lever.co/newer",
                last=NOW - timedelta(days=2))                    # 2d + 60h
    atns = _co(db, "ATNS",
               url="https://atns.ci.hr/applicant/index.php?controller=Page&name=jobsearch",
               last=NOW - timedelta(days=1))                     # 1d + 60h
    parsed = _co(db, "AlreadyParsed", url="https://boards.greenhouse.io/parsed",
                 last=NOW - timedelta(days=3, hours=12),
                 success_at=NOW - timedelta(days=3, hours=12))   # 3.5d + 36h
    db.add_all([
        Company(company_name=f"KenyaHtml{i}", careers_url="https://example.co.ke/careers", country="Kenya")
        for i in range(220)
    ])
    db.commit()

    ids = select_due_company_ids(db, limit=300, now=NOW)
    assert ids[:2] == [botswana.id, nigeria.id]                 # never scanned: SADC, Africa
    assert all(db.get(Company, i).country == "Kenya" for i in ids[2:222])
    assert ids[222:] == [australia.id, older.id, parsed.id, newer.id, atns.id]
    assert select_due_company_ids(db, limit=300, now=NOW) == ids


def test_other_regions_are_not_starved(db):
    """The region lead is bounded: a source elsewhere that has waited long
    enough goes ahead of a South African one."""
    sa = _co(db, "SA", last=NOW - timedelta(hours=30))                       # 30 + 36 = 66
    kenya_recent = _co(db, "KenyaRecent", country="Kenya",
                       last=NOW - timedelta(hours=50))                      # 50 + 12 = 62
    kenya_old = _co(db, "KenyaOld", country="Kenya", last=NOW - timedelta(hours=72))  # 84
    au_old = _co(db, "AustraliaOld", country="Australia",
                 last=NOW - timedelta(hours=70))                            # 70
    ids = select_due_company_ids(db, limit=10, now=NOW)
    assert ids == [kenya_old.id, au_old.id, sa.id, kenya_recent.id]


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
