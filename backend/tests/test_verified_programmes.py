"""Official programme pages: store named open calls, and a closing date only when stated."""
from datetime import date, datetime, timedelta, timezone

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.migrations.verified_programmes import downgrade, upgrade
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.services.verified_programmes import (
    external_id_for, import_verified_programmes, load_programme_file,
)


VERIFIED_ON = datetime(2026, 11, 9, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _on_the_verified_day(monkeypatch):
    """Run the import as on the day the file was checked.

    The shipped file holds real closing dates. Once a date passes the importer
    skips that row, so without a fixed day these counts would change over time.
    """
    monkeypatch.setattr(
        "app.services.opportunity_expiry.sa_today",
        lambda moment=None: VERIFIED_ON.date(),
    )


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _company(db, name, *, active=True, careers="https://example.com/careers"):
    row = Company(
        company_name=name, country="South Africa", source_type="PRIVATE",
        active=active, careers_url=careers,
    )
    db.add(row)
    db.commit()
    return row


def test_shipped_file_names_only_programme_types_and_open_dates():
    verified_on, records = load_programme_file()
    assert verified_on == VERIFIED_ON
    assert records
    kinds = set()
    for record in records:
        assert record["opportunity_type"] in ("internship", "learnership", "bursary", "graduate_programme")
        assert record["source_url"].startswith("https://")
        assert record["country"] == "South Africa"
        kinds.add(record["company_name"])
        field = record.get("field_of_study") or ""
        assert len(field) <= 400
        stated = record.get("closing_date")
        if stated is not None:
            day = datetime.strptime(stated, "%Y-%m-%d").date()
            assert day < verified_on.date()
    assert kinds == {
        "Absa Group", "Deloitte Southern Africa", "EY South Africa",
        "CHIETA", "National Student Financial Aid Scheme (NSFAS)",
    }


def test_import_matches_existing_employers_and_leaves_closing_dates_blank():
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    absa = _company(db, "Absa Group", careers="https://www.absa.africa/careers/")
    earlier = datetime(2026, 1, 1, tzinfo=timezone.utc)
    careers = VacancySource(
        company_id=absa.id, url="https://www.absa.africa/careers/", ats_type="workday",
        active=True, created_at=earlier,
    )
    db.add(careers)
    db.commit()
    absa_id = absa.id
    _company(db, "Deloitte Southern Africa", careers="https://www.deloitte.com/za/en/careers.html")
    _company(db, "EY South Africa", active=False, careers="https://www.ey.com/en_za/careers/job-search")
    _company(db, "CHIETA", careers="https://chieta.org.za/careers/vacancies/")
    _company(db, "National Student Financial Aid Scheme (NSFAS)", careers="https://www.nsfas.org.za/content/careers.html")
    db.close()

    first = import_verified_programmes(engine)
    assert first["created"] == 20
    assert first["skipped_expired"] == 5
    assert first["skipped_missing_company"] == 0
    assert first["skipped_invalid"] == 0

    db = S()
    rows = db.query(Vacancy).all()
    assert len(rows) == 20
    assert all(row.posting_date is None for row in rows)
    assert all(row.closing_date is None for row in rows if row.title in {
        "Absa Graduate Programme", "Bursary Programme",
    })
    assert all(row.stipend_text is None for row in rows if row.title in {
        "Absa Graduate Programme", "Bursary Programme",
    })
    assert all(_as_utc(row.verified_at) == VERIFIED_ON for row in rows)
    bursaries = [row for row in rows if row.opportunity_type == "bursary"]
    assert {row.title for row in bursaries} == {"Absa bursary Programme"}
    forensic = next(row for row in rows if row.title.startswith("Forensic"))
    assert forensic.field_of_study.startswith("BCom/BCom Honours")
    assert "30 April" not in (forensic.description or "")

    absa_sources = (
        db.query(VacancySource)
        .filter(VacancySource.company_id == absa_id)
        .order_by(VacancySource.created_at.asc())
        .all()
    )
    assert absa_sources[0].ats_type == "workday"
    assert absa_sources[0].active is True
    assert absa_sources[1].ats_type == "verified_page"
    assert absa_sources[1].active is False
    assert absa_sources[1].created_at >= absa_sources[0].created_at

    db.close()

    again = import_verified_programmes(engine)
    assert again["created"] == 0
    assert again["updated"] == 20
    assert again["skipped_expired"] == 5
    db = S()
    assert db.query(Vacancy).count() == 20
    db.close()
    engine.dispose()


def test_unknown_company_and_duplicate_title_are_skipped():
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    absa = _company(db, "Absa Group")
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    source = VacancySource(company_id=absa.id, url="https://www.absa.africa/careers/", ats_type="workday")
    db.add(source)
    db.commit()
    db.add(Vacancy(
        company_id=absa.id, source_id=source.id, title="Absa Graduate Programme",
        content_hash="existing", external_id="board-1", is_open=True,
        first_seen_at=now, last_seen_at=now,
    ))
    db.commit()
    db.close()

    counts = import_verified_programmes(engine)
    assert counts["skipped_missing_company"] == 20
    assert counts["skipped_duplicate_title"] == 1
    assert counts["created"] == 4
    db = S()
    titled = db.query(Vacancy).filter(Vacancy.title == "Absa Graduate Programme").all()
    assert len(titled) == 1
    assert titled[0].external_id == "board-1"
    db.close()
    engine.dispose()


def test_invalid_record_is_not_stored_and_a_passed_date_is_not_added(monkeypatch):
    monkeypatch.setattr(
        "app.services.opportunity_expiry.sa_today",
        lambda moment=None: date(2026, 10, 13),
    )
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    _company(db, "Absa Group")
    db.close()
    counts = import_verified_programmes(engine, verified_on=VERIFIED_ON, records=[
        {
            "company_name": "Absa Group",
            "country": "South Africa",
            "title": "Scholarship",
            "opportunity_type": "scholarship",
            "source_url": "https://www.absa.africa/careers/graduate-opportunities/",
            "closing_date": "2026-04-30",
        },
        {
            "company_name": "Absa Group",
            "country": "South Africa",
            "title": "Absa bursary Programme",
            "opportunity_type": "bursary",
            "source_url": "https://www.absa.africa/careers/graduate-opportunities/",
            "description": "We select a handful of talented top performers.",
            "closing_date": "2026-04-30",
        },
        {
            "company_name": "Absa Group",
            "country": "South Africa",
            "title": "ICT Intern",
            "opportunity_type": "internship",
            "source_url": "https://chieta.org.za/job/24-months-internship-ict-intern/",
            "description": "24 MONTHS INTERNSHIP: ICT INTERN.",
            "closing_date": "2026-10-23",
        },
        {
            "company_name": "Absa Group",
            "country": "South Africa",
            "title": "Open bursary",
            "opportunity_type": "bursary",
            "source_url": "https://www.absa.africa/careers/graduate-opportunities/",
            "closing_date": "next Friday",
        },
    ])
    assert counts["skipped_invalid"] == 1
    assert counts["skipped_expired"] == 1
    assert counts["created"] == 2
    db = S()
    assert db.query(Vacancy).filter(Vacancy.title == "Absa bursary Programme").count() == 0
    ict = db.query(Vacancy).filter(Vacancy.title == "ICT Intern").one()
    assert ict.closing_date == date(2026, 10, 23)
    vague = db.query(Vacancy).filter(Vacancy.title == "Open bursary").one()
    assert vague.closing_date is None
    assert ict.external_id == external_id_for(
        "Absa Group", "ICT Intern",
        "https://chieta.org.za/job/24-months-internship-ict-intern/",
    )
    db.close()
    engine.dispose()


def test_downgrade_removes_only_the_verified_rows():
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    absa = _company(db, "Absa Group")
    source = VacancySource(company_id=absa.id, url="https://www.absa.africa/careers/", ats_type="workday")
    db.add(source)
    db.commit()
    kept = Vacancy(
        company_id=absa.id, source_id=source.id, title="Teller", content_hash="job",
        external_id="board-teller", is_open=True,
        first_seen_at=VERIFIED_ON, last_seen_at=VERIFIED_ON,
    )
    db.add(kept)
    db.commit()
    kept_id = kept.id
    db.close()

    upgrade(engine)
    downgrade(engine)
    db = S()
    remaining = db.query(Vacancy).all()
    assert [row.id for row in remaining] == [kept_id]
    assert db.query(VacancySource).filter(VacancySource.ats_type == "verified_page").count() == 0
    assert db.query(VacancySource).filter(VacancySource.ats_type == "workday").count() == 1
    db.close()

    upgrade(engine)
    db = S()
    assert db.query(Vacancy).filter(Vacancy.external_id.like("verified:%")).count() == 5
    assert db.get(Vacancy, kept_id).title == "Teller"
    db.close()
    engine.dispose()


def test_a_closing_date_that_has_passed_is_skipped_and_counted(monkeypatch):
    monkeypatch.setattr(
        "app.services.opportunity_expiry.sa_today",
        lambda moment=None: date(2026, 10, 23) + timedelta(days=1),
    )
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    _company(db, "Absa Group")
    db.close()
    counts = import_verified_programmes(engine, verified_on=VERIFIED_ON, records=[
        {
            "company_name": "Absa Group",
            "country": "South Africa",
            "title": "ICT Intern",
            "opportunity_type": "internship",
            "source_url": "https://chieta.org.za/job/24-months-internship-ict-intern/",
            "description": "24 MONTHS INTERNSHIP: ICT INTERN.",
            "closing_date": "2026-10-23",
        },
    ])
    assert counts["skipped_expired"] == 1
    assert counts["created"] == 0
    db = S()
    assert db.query(Vacancy).count() == 0
    db.close()
    engine.dispose()


def test_a_call_that_closes_is_marked_expired_and_kept(monkeypatch):
    monkeypatch.setattr(
        "app.services.opportunity_expiry.sa_today",
        lambda moment=None: date(2026, 9, 1),
    )
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    _company(db, "Absa Group", careers="https://www.absa.africa/careers/")
    _company(db, "Deloitte Southern Africa", careers="https://www.deloitte.com/za/en/careers.html")
    _company(db, "EY South Africa", active=False, careers="https://www.ey.com/en_za/careers/job-search")
    _company(db, "CHIETA", careers="https://chieta.org.za/careers/vacancies/")
    _company(db, "National Student Financial Aid Scheme (NSFAS)", careers="https://www.nsfas.org.za/content/careers.html")
    db.close()

    first = import_verified_programmes(engine)
    assert first["created"] == 25
    monkeypatch.setattr(
        "app.services.opportunity_expiry.sa_today",
        lambda moment=None: date(2026, 11, 9),
    )
    again = import_verified_programmes(engine)
    assert again["created"] == 0
    assert again["updated"] == 25
    db = S()
    assert db.query(Vacancy).filter(Vacancy.deleted_at.is_(None)).count() == 25
    closed_titles = {
        "Bursary Programme",
        "Human Resource Intern",
        "Administration Intern",
        "ICT Intern",
        "Apply for NSFAS funding for the 2027 academic year",
    }
    for row in db.query(Vacancy).all():
        if row.title in closed_titles:
            assert row.is_open is False and row.status == "expired" and row.deleted_at is None
        else:
            assert row.is_open is True and row.status == "active"
    ey = db.query(Vacancy).filter(Vacancy.title == "Bursary Programme").one()
    assert ey.closing_date == date(2026, 9, 30)
    assert ey.source_url == "https://www.ey.com/en_za/careers/apply-for-our-bursary-program"
    nsfas = db.query(Vacancy).filter(Vacancy.title.startswith("Apply for NSFAS")).one()
    assert nsfas.closing_date == date(2026, 10, 31)
    assert _as_utc(nsfas.verified_at) == datetime(2026, 10, 13, tzinfo=timezone.utc)
    db.close()
    engine.dispose()


def test_an_existing_call_keeps_one_row_when_its_source_url_changes(monkeypatch):
    monkeypatch.setattr(
        "app.services.opportunity_expiry.sa_today",
        lambda moment=None: date(2026, 11, 9),
    )
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    company = _company(db, "EY South Africa", active=False, careers="https://www.ey.com/en_za/careers/job-search")
    source = VacancySource(company_id=company.id, url="https://www.ey.com/en_za/careers/job-search", ats_type="workday")
    db.add(source)
    db.commit()
    old_url = "https://www.ey.com/en_za/careers/graduate-programmes-south-africa"
    now = datetime(2026, 10, 13, tzinfo=timezone.utc)
    db.add(Vacancy(
        company_id=company.id, source_id=source.id, title="Bursary Programme",
        content_hash="old", external_id=external_id_for("EY South Africa", "Bursary Programme", old_url),
        is_open=True, first_seen_at=now, last_seen_at=now,
    ))
    db.commit()
    db.close()
    counts = import_verified_programmes(engine, verified_on=VERIFIED_ON, records=[{
        "company_name": "EY South Africa",
        "country": "South Africa",
        "title": "Bursary Programme",
        "opportunity_type": "bursary",
        "source_url": "https://www.ey.com/en_za/careers/apply-for-our-bursary-program",
        "previous_source_url": old_url,
        "description": "Bursary applications are open from the 1st of July to the 30th of September 2026.",
        "closing_date": "2026-09-30",
    }])
    assert counts["updated"] == 1
    assert counts["created"] == 0
    db = S()
    rows = db.query(Vacancy).all()
    assert len(rows) == 1
    assert rows[0].is_open is False and rows[0].status == "expired" and rows[0].deleted_at is None
    assert rows[0].closing_date == date(2026, 9, 30)
    assert rows[0].source_url == "https://www.ey.com/en_za/careers/apply-for-our-bursary-program"
    db.close()
    engine.dispose()


def test_a_manually_closed_programme_is_not_reopened_on_boot():
    engine = _engine()
    S = sessionmaker(bind=engine)
    db = S()
    _company(db, "Absa Group")
    db.close()
    import_verified_programmes(engine)
    db = S()
    row = db.query(Vacancy).filter(Vacancy.title == "SAICA Trainee Programme").one()
    row.quality_flags = ["manual_close"]
    row.is_open = False
    row.status = "expired"
    row.lifecycle_status = "REMOVED"
    db.commit()
    db.close()
    again = import_verified_programmes(engine)
    assert again["skipped_closed"] == 1
    db = S()
    row = db.query(Vacancy).filter(Vacancy.title == "SAICA Trainee Programme").one()
    assert row.is_open is False and row.status == "expired" and row.lifecycle_status == "REMOVED"
    db.close()
    engine.dispose()
