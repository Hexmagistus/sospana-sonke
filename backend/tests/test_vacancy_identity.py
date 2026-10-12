"""One vacancy row when the description changes and the employer id does not.

Extra open rows that already share that id are reported. The scan does not
delete them.
"""
import time
from datetime import datetime, timedelta, timezone

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.scraper.base import RawVacancy
from app.scraper.fingerprint import vacancy_fingerprint
from app.services.duplicate_service import find_external_id_groups
from app.services.scan_service import FetchOutcome, apply_fetch
from tests.conftest import make_admin, register_and_login

NOW = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)


def _company(db):
    company = Company(
        company_name="Ward Hospital", country="South Africa", source_type="HOSPITAL",
        careers_url="https://ward.example/careers", active=True,
    )
    db.add(company)
    db.commit()
    source = VacancySource(
        company_id=company.id, url="https://ward.example/careers", ats_type="static", active=True,
    )
    db.add(source)
    db.commit()
    return company, source


def _row(db, company, source, *, external_id, title, description, fingerprint, hours_old, content_hash):
    seen = NOW - timedelta(hours=hours_old)
    row = Vacancy(
        company_id=company.id, source_id=source.id, external_id=external_id, title=title,
        location="Cape Town", description=description, fingerprint=fingerprint,
        content_hash=content_hash, is_open=True, lifecycle_status="ACTIVE",
        first_seen_at=seen, last_seen_at=seen,
    )
    db.add(row)
    db.commit()
    return row


def _scan(db, source, description, external_id="req-9"):
    outcome = FetchOutcome(
        kind="ok", started=time.monotonic(), now=NOW, ats_type="static", parser_used="static",
        raw_list=[RawVacancy(
            title="Professional Nurse", external_id=external_id, location="Cape Town",
            description=description, application_url="https://ward.example/apply/nurse",
        )],
    )
    return apply_fetch(db, source, outcome)


def test_description_change_with_the_same_external_id_updates_one_row(db):
    company, source = _company(db)
    stale = vacancy_fingerprint(company.id, None, "Professional Nurse", "Cape Town")
    original = _row(
        db, company, source, external_id="REQ-9", title="Professional Nurse",
        description="Old wording.", fingerprint=stale, hours_old=5, content_hash="old-hash",
    )
    report = _scan(db, source, "Updated ward wording for the same requisition.")
    rows = db.query(Vacancy).filter(Vacancy.company_id == company.id).all()
    assert report.created == 0 and report.updated == 1
    assert len(rows) == 1
    assert rows[0].id == original.id
    assert "Updated ward wording" in (rows[0].description or "")
    assert rows[0].deleted_at is None and rows[0].is_open is True


def test_shared_external_id_rows_stay_open_and_are_reported(client, db, db_engine):
    company, source = _company(db)
    older = _row(
        db, company, source, external_id="REQ-9", title="Nurse morning",
        description="Older copy.", fingerprint="fp-older", hours_old=48, content_hash="hash-older",
    )
    newer = _row(
        db, company, source, external_id="req-9", title="Nurse afternoon",
        description="Newer copy.", fingerprint="fp-newer", hours_old=24, content_hash="hash-newer",
    )
    first = _scan(db, source, "First pass wording.")
    second = _scan(db, source, "Second pass wording.")
    assert first.created == 0 and second.created == 0
    db.expire_all()
    kept = db.query(Vacancy).filter(Vacancy.company_id == company.id).order_by(Vacancy.first_seen_at).all()
    assert [row.id for row in kept] == [older.id, newer.id]
    assert all(row.is_open and row.deleted_at is None for row in kept)
    assert "Second pass wording" in (kept[0].description or "")
    assert kept[1].description == "Newer copy."
    assert (kept[1].consecutive_misses or 0) == 0

    groups = find_external_id_groups(db, company_id=company.id)
    assert groups == [{
        "company_id": company.id,
        "external_id": "req-9",
        "vacancy_ids": [older.id, newer.id],
    }]
    before = [(row.id, row.is_open, row.deleted_at, row.description) for row in kept]

    admin_email, admin_password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password}).json()
    listed = client.get(
        "/api/v1/admin/vacancies/external-id-duplicates",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json() == groups

    _, tokens = register_and_login(client, email="reader@example.com")
    refused = client.get(
        "/api/v1/admin/vacancies/external-id-duplicates",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert refused.status_code == 403
    db.expire_all()
    after = db.query(Vacancy).filter(Vacancy.company_id == company.id).order_by(Vacancy.first_seen_at).all()
    assert [(row.id, row.is_open, row.deleted_at, row.description) for row in after] == before
