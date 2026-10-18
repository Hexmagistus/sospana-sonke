"""Opportunity type: conservative labels, a reversible migration, public counts."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.migrations.opportunity_types import downgrade, upgrade
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.services.opportunity_type import (
    JOB, classify_opportunity, classify_stored, stated_field_of_study, stated_stipend,
)
from app.services.scan_service import _COPY_IF_PRESENT, _apply_fields


# Relative to the real clock: public lists hide roles not seen for 7 days
# and roles whose closing day has passed.
NOW = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=5)


def test_title_names_one_programme_and_unclear_text_stays_a_job():
    assert classify_opportunity("ELETRONICS NQF LEVEL 3 LEARNERSHIP") == "learnership"
    assert classify_opportunity("apply for a bursary") == "bursary"
    assert classify_opportunity("Bursaries for 2026") == "bursary"
    assert classify_opportunity("MUNICIPAL FINANCE MANAGEMENT INTERNSHIP ADVERT") == "internship"
    assert classify_opportunity("Finance Intern") == "internship"
    assert classify_opportunity("Graduate Programme 2027") == "graduate_programme"
    assert classify_opportunity("Graduate Program in Finance") == "graduate_programme"
    assert classify_opportunity("Graduate Engineer") == JOB
    assert classify_opportunity("Postgraduate Programme") == JOB
    assert classify_opportunity("Internal Auditor") == JOB
    assert classify_opportunity("INTERNATIONAL OFFICE") == JOB
    assert classify_opportunity("Learnership and Internship") == JOB
    assert classify_opportunity("Nurse", "Applicants must have completed a learnership.") == JOB
    assert classify_opportunity("Technician", "This learnership covers electrical work.") == "learnership"
    assert classify_opportunity(None) == JOB
    assert classify_opportunity("") == JOB


def test_field_and_stipend_are_copied_only_when_labelled():
    text = "field of study: Accounting\nstipend of R4 500 per month"
    assert stated_field_of_study("Bursary", text) == "Accounting"
    assert stated_stipend("Bursary", text) == "R4 500 per month"
    assert stated_field_of_study("Learnership in engineering", "Open to students.") is None
    assert stated_stipend("Internship", "Paid work experience.") is None


def test_scan_apply_labels_the_row_and_does_not_invent_a_closing_date():
    vac = Vacancy(
        company_id="c", source_id="s", title="Old", content_hash="h",
        is_open=True, first_seen_at=NOW, last_seen_at=NOW,
    )
    fields = {key: None for key in _COPY_IF_PRESENT}
    fields.update(
        title="Bursary for accounting",
        description="field of study: Accounting\nfunding amount: R20 000",
        content_hash="h2", fingerprint="f", quality_score=1, lifecycle_status="ACTIVE",
    )
    _apply_fields(vac, fields, NOW)
    assert vac.opportunity_type == "bursary"
    assert vac.field_of_study == "Accounting"
    assert vac.stipend_text == "R20 000"
    assert vac.closing_date is None
    assert vac.verified_at == NOW
    assert vac.opportunity_reviewed is True


def test_migration_classifies_then_drops_the_columns():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    S = sessionmaker(bind=engine)
    db = S()
    company = Company(company_name="College", country="South Africa", source_type="COLLEGE", active=True)
    db.add(company)
    db.commit()
    source = VacancySource(company_id=company.id, url="https://college.example/careers", ats_type="static")
    db.add(source)
    db.commit()
    row = Vacancy(
        company_id=company.id, source_id=source.id, title="Learnership: Food handling",
        description="field of study: Hospitality", content_hash="hash-learn",
        is_open=True, first_seen_at=NOW, last_seen_at=NOW, opportunity_reviewed=False,
    )
    plain = Vacancy(
        company_id=company.id, source_id=source.id, title="Internal Auditor",
        description="must have completed a learnership", content_hash="hash-job",
        is_open=True, first_seen_at=NOW, last_seen_at=NOW, opportunity_reviewed=False,
    )
    db.add_all([row, plain])
    db.commit()
    row_id, plain_id = row.id, plain.id
    db.close()

    changed = classify_stored(engine)
    assert changed == 1
    db = S()
    labelled = db.get(Vacancy, row_id)
    untouched = db.get(Vacancy, plain_id)
    assert labelled.opportunity_type == "learnership"
    assert labelled.field_of_study == "Hospitality"
    assert labelled.verified_at is not None
    assert labelled.closing_date is None
    assert untouched.opportunity_type == JOB
    assert untouched.verified_at is None
    assert untouched.opportunity_reviewed is True
    db.close()

    downgrade(engine)
    names = {col["name"] for col in inspect(engine).get_columns("vacancies")}
    assert "opportunity_type" not in names
    assert "field_of_study" not in names
    assert "stipend_text" not in names
    assert "verified_at" not in names
    assert "opportunity_reviewed" not in names

    upgrade(engine)
    db = S()
    again = db.get(Vacancy, row_id)
    assert again.opportunity_type == "learnership"
    assert again.title == "Learnership: Food handling"
    db.close()
    engine.dispose()


def test_public_jobs_filter_and_counts_by_type(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    company = Company(company_name="City Works", country="South Africa", source_type="MUNI", active=True)
    s.add(company)
    s.commit()
    now = datetime.now(timezone.utc)
    rows = [
        ("Nurse", "job"),
        ("Finance Internship", "internship"),
        ("Electrical Learnership", "learnership"),
    ]
    ids = {}
    for title, kind in rows:
        vac = Vacancy(
            company_id=company.id, source_id="src-x", title=title, content_hash=title,
            is_open=True, first_seen_at=now, last_seen_at=now, opportunity_type=kind,
            opportunity_reviewed=True,
        )
        s.add(vac)
        s.commit()
        ids[kind] = vac.id
    s.close()

    listed = client.get("/api/v1/jobs", params={"opportunity_type": "learnership"})
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["matched"] == 1
    assert body["jobs"][0]["id"] == ids["learnership"]
    assert body["jobs"][0]["opportunity_type"] == "learnership"
    assert client.get("/api/v1/jobs", params={"opportunity_type": "scholarship"}).status_code == 422
    counts = client.get("/api/v1/jobs/counts").json()["counts"]
    assert counts["job"] >= 1
    assert counts["internship"] >= 1
    assert counts["learnership"] >= 1
    assert counts["bursary"] == 0
    assert counts["graduate_programme"] == 0

    from datetime import date as date_cls
    s = S()
    soon = s.get(Vacancy, ids["internship"])
    soon.closing_date = date.today() + timedelta(days=30)
    later = s.get(Vacancy, ids["learnership"])
    later.closing_date = date.today() + timedelta(days=50)
    s.commit()
    s.close()
    dated = client.get("/api/v1/jobs", params={"sort": "closing"})
    assert dated.status_code == 200
    ordered = [row["title"] for row in dated.json()["jobs"]]
    assert ordered.index("Finance Internship") < ordered.index("Electrical Learnership")
    assert ordered.index("Electrical Learnership") < ordered.index("Nurse")
    nurse = next(row for row in dated.json()["jobs"] if row["title"] == "Nurse")
    assert nurse["closing_date"] is None
