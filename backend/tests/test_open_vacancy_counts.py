"""Directory cards report how many open vacancies we actually hold."""
from datetime import datetime, timezone

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.services.vacancy_counts import companies_with_known_vacancy_count, open_vacancy_counts
from tests.conftest import register_and_login


def _company(db, name, url, checked=None):
    company = Company(
        company_name=name, country="Kenya", source_type="PRIVATE",
        careers_url=url, active=True, last_checked=checked,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    source = VacancySource(company_id=company.id, url=url or "https://example.com/careers")
    db.add(source)
    db.commit()
    db.refresh(source)
    return company, source


def _vacancy(db, company, source, title, *, is_open=True, lifecycle=None, deleted=False):
    now = datetime.now(timezone.utc)
    row = Vacancy(
        company_id=company.id, source_id=source.id, title=title,
        content_hash=f"h-{title}", is_open=is_open, lifecycle_status=lifecycle,
        first_seen_at=now, last_seen_at=now,
        deleted_at=now if deleted else None,
    )
    db.add(row)
    db.commit()
    return row


def test_open_counts_keep_active_and_null_and_drop_the_rest(db):
    checked = datetime(2026, 10, 1, tzinfo=timezone.utc)
    absa, absa_src = _company(db, "Absa", "https://absa.example/careers", checked)
    other, other_src = _company(db, "Clinic", "https://clinic.example/jobs")
    empty, _ = _company(db, "Quiet Bank", None)

    _vacancy(db, absa, absa_src, "Nurse", lifecycle="ACTIVE")
    _vacancy(db, absa, absa_src, "Clerk", lifecycle=None)
    _vacancy(db, absa, absa_src, "Open word", lifecycle="OPEN")
    _vacancy(db, absa, absa_src, "Closed lifecycle", lifecycle="CLOSED")
    _vacancy(db, absa, absa_src, "Expired", lifecycle="EXPIRED")
    _vacancy(db, absa, absa_src, "Shut", is_open=False, lifecycle="ACTIVE")
    _vacancy(db, absa, absa_src, "Removed row", lifecycle="ACTIVE", deleted=True)
    _vacancy(db, other, other_src, "Other role", lifecycle="ACTIVE")

    counts = open_vacancy_counts(db, [absa.id, other.id, empty.id, "missing"])
    assert counts == {absa.id: 3, other.id: 1}
    assert "ix_vacancies_company_open" in {ix.name for ix in Vacancy.__table__.indexes}


def test_company_list_returns_the_count_without_dropping_fields(client, db):
    checked = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)
    company, source = _company(db, "Gold Board", "https://gold.example/careers", checked)
    _vacancy(db, company, source, "Analyst", lifecycle="ACTIVE")
    _vacancy(db, company, source, "Old", lifecycle="REMOVED")

    _, tokens = register_and_login(client)
    listed = client.get(
        "/api/v1/companies", params={"country": "Kenya"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json() if item["id"] == company.id)
    assert row["open_vacancies"] == 1
    assert row["open_vacancies_known"] is True
    assert row["careers_url"] == "https://gold.example/careers"
    assert row["company_name"] == "Gold Board"
    assert row["last_checked"].startswith("2026-10-02")
    assert row["country"] == "Kenya"


def test_unparsed_board_is_not_a_confirmed_zero(db):
    now = datetime(2026, 10, 3, tzinfo=timezone.utc)
    held, held_src = _company(db, "Held Roles", "https://held.example/careers")
    _vacancy(db, held, held_src, "Controller", lifecycle="ACTIVE")
    static_empty, static_src = _company(db, "Static Empty", "https://static.example/careers")
    cihr_empty, cihr_src = _company(db, "Cihr Empty", "https://atns.ci.hr/applicant/index.php")
    never, _ = _company(db, "Never Parsed", "https://never.example/careers")
    success, success_src = _company(db, "Parsed Then Closed", "https://boards.greenhouse.io/acme")
    changed, changed_src = _company(db, "Structure Changed", "https://eskomcareers.ci.hr/applicant")

    static_src.last_success_at = now
    static_src.scraper_status = "NO_VACANCIES"
    static_src.parser_used = "static"
    cihr_src.last_success_at = now
    cihr_src.scraper_status = "NO_VACANCIES"
    cihr_src.parser_used = "cihr"
    success_src.last_success_at = now
    success_src.scraper_status = "SUCCESS"
    success_src.parser_used = "greenhouse"
    changed_src.last_success_at = now
    changed_src.scraper_status = "SITE_CHANGED"
    changed_src.parser_used = "cihr"
    db.commit()

    known = companies_with_known_vacancy_count(db, [
        held.id, static_empty.id, cihr_empty.id, never.id, success.id, changed.id,
    ])
    assert known == {cihr_empty.id, success.id}
    assert held.id not in known


def test_company_list_hides_an_unparsed_zero(client, db):
    company, _ = _company(db, "ATNS", "https://atns.ci.hr/applicant/index.php?controller=Page&name=jobsearch")
    _, tokens = register_and_login(client)
    listed = client.get(
        "/api/v1/companies", params={"country": "Kenya"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json() if item["id"] == company.id)
    assert row["open_vacancies"] == 0
    assert row["open_vacancies_known"] is False
