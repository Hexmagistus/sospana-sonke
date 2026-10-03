"""Tests for standalone scheduler job functions not covered elsewhere."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from app.models.company import Company
from app.models.notification import JobRun
from app.models.vacancy import Vacancy
from app.scheduler.jobs import close_expired_vacancies, scan_due_companies
from app.scheduler.registry import JOBS, DEFAULT_SCHEDULE
from app.scheduler.runner import run_job


def _mk_vacancy(db, title, closing_date=None, is_open=True):
    company = Company(company_name=f"Co-{title}", careers_url="https://boards.greenhouse.io/co")
    db.add(company); db.commit(); db.refresh(company)
    now = datetime.now(timezone.utc)
    vac = Vacancy(company_id=company.id, source_id="s1", title=title, content_hash=f"h-{title}",
                  is_open=is_open, closing_date=closing_date, first_seen_at=now, last_seen_at=now)
    db.add(vac); db.commit(); db.refresh(vac)
    return vac


def test_close_expired_vacancies_closes_only_past_closing_date(db):
    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)
    expired = _mk_vacancy(db, "Expired Role", closing_date=yesterday)
    still_open = _mk_vacancy(db, "Live Role", closing_date=tomorrow)
    no_closing_date = _mk_vacancy(db, "No Closing Date Role", closing_date=None)
    already_closed = _mk_vacancy(db, "Already Closed", closing_date=yesterday, is_open=False)

    result = close_expired_vacancies(db)

    assert result["vacancies_closed"] == 1
    db.refresh(expired); db.refresh(still_open); db.refresh(no_closing_date); db.refresh(already_closed)
    assert expired.is_open is False
    assert expired.lifecycle_status == "EXPIRED"
    assert still_open.is_open is True
    assert no_closing_date.is_open is True
    assert already_closed.is_open is False


def test_close_expired_vacancies_registered_in_scheduler():
    assert "close_expired_vacancies" in JOBS
    assert "close_expired_vacancies" in DEFAULT_SCHEDULE


def test_scan_due_companies_advances_after_a_database_error(db, monkeypatch):
    """A failed insert must not abort the cron request or pin that employer first."""
    now = datetime.now(timezone.utc)
    bad = Company(
        company_name="Absa", country="South Africa", active=True,
        careers_url="https://absa.wd3.myworkdayjobs.com/ABSAcareers",
    )
    good = Company(
        company_name="Clinic", country="South Africa", active=True,
        careers_url="https://boards.greenhouse.io/clinic",
        last_checked=now - timedelta(days=2),
    )
    db.add_all([bad, good])
    db.commit()
    seen: list[str] = []

    def _scan(session, company, client=None, check_robots=True):
        seen.append(company.company_name)
        if company.company_name == "Absa":
            session.execute(text("SELECT * FROM table_that_does_not_exist"))
        return []

    monkeypatch.setattr("app.scheduler.jobs.scan_company", _scan)
    out = scan_due_companies(db, limit=10, max_seconds=55)

    assert seen[0] == "Absa"
    assert "Clinic" in seen
    assert out["sources_failed"] >= 1
    db.expire_all()
    absa = db.query(Company).filter(Company.company_name == "Absa").one()
    assert absa.last_checked is not None


def test_run_job_records_an_error_when_the_statement_fails(db, monkeypatch):
    def _bad(session, job_run_id=None):
        session.execute(text("SELECT * FROM table_that_does_not_exist"))

    monkeypatch.setitem(JOBS, "close_expired_vacancies", _bad)
    run = run_job(db, "close_expired_vacancies")
    assert run.status == "error"
    assert run.finished_at is not None
    db.expire_all()
    stored = db.get(JobRun, run.id)
    assert stored is not None
    assert stored.status == "error"
