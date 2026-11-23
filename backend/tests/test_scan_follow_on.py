"""The background follow-on that keeps scanning after the cron request."""
from app.services import scan_follow_on
from app.services.scan_follow_on import BATCH_SECONDS, run_follow_on


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_stops_when_nothing_is_due():
    clock = FakeClock()
    results = iter([{"due_selected": 60, "companies_scanned": 50, "vacancies_created": 7},
                    {"due_selected": 12, "companies_scanned": 12, "vacancies_created": 1},
                    {"due_selected": 0, "companies_scanned": 0}])

    def batch():
        clock.t += 30
        return next(results)

    totals = run_follow_on(batch, 480, clock)
    assert totals["batches"] == 3
    assert totals["companies_scanned"] == 62
    assert totals["vacancies_created"] == 8
    assert totals["stopped"] == "nothing_due"


def test_never_starts_a_batch_that_would_run_past_the_window():
    clock = FakeClock()
    calls = []

    def batch():
        calls.append(clock.t)
        clock.t += BATCH_SECONDS
        return {"due_selected": 60, "companies_scanned": 60}

    totals = run_follow_on(batch, 480, clock)
    assert totals["stopped"] == "time"
    assert all(start + BATCH_SECONDS <= 480 for start in calls)
    assert totals["batches"] == len(calls) == int(480 // BATCH_SECONDS)


def test_gives_up_after_repeated_errors():
    clock = FakeClock()

    def batch():
        clock.t += 1
        raise RuntimeError("database away")

    totals = run_follow_on(batch, 480, clock)
    assert totals["errors"] == 3 and totals["stopped"] == "errors"


def test_switched_off_under_test_env_and_by_zero(monkeypatch):
    assert scan_follow_on.follow_on_seconds() == 0.0
    assert scan_follow_on.start_follow_on() is False
    from app.core.config import settings
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setenv("SCAN_FOLLOW_ON_SECONDS", "0")
    assert scan_follow_on.start_follow_on() is False
    monkeypatch.setenv("SCAN_FOLLOW_ON_SECONDS", "300")
    assert scan_follow_on.follow_on_seconds() == 300.0


def test_cron_scan_reports_follow_on_flag(client, db, monkeypatch):
    from app.scheduler import jobs
    monkeypatch.setattr("app.services.scan_batch.run_scan_batch",
                        lambda db, **kw: {"due_selected": 0, "companies_scanned": 0})
    started = []
    monkeypatch.setattr(scan_follow_on, "start_follow_on", lambda: started.append(1) or True)
    assert jobs.scan_due_companies(db)["due_selected"] == 0
    assert started == []
    assert jobs.scan_due_companies(db, job_run_id="run-1")["follow_on_started"] is True
    assert started == [1]
