"""Directory cards report how many open vacancies we actually hold."""
from datetime import datetime, timezone

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.services.vacancy_counts import open_vacancy_counts
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
    assert row["careers_url"] == "https://gold.example/careers"
    assert row["company_name"] == "Gold Board"
    assert row["last_checked"].startswith("2026-10-02")
    assert row["country"] == "Kenya"
