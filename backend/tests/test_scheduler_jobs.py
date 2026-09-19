"""Tests for standalone scheduler job functions not covered elsewhere."""
from datetime import date, datetime, timedelta, timezone

from app.models.company import Company
from app.models.vacancy import Vacancy
from app.scheduler.jobs import close_expired_vacancies
from app.scheduler.registry import JOBS, DEFAULT_SCHEDULE


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
    assert still_open.is_open is True
    assert no_closing_date.is_open is True
    assert already_closed.is_open is False


def test_close_expired_vacancies_registered_in_scheduler():
    assert "close_expired_vacancies" in JOBS
    assert "close_expired_vacancies" in DEFAULT_SCHEDULE
