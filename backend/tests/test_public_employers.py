"""Public employer pages: careers links only, no notes, open roles with source links."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource


def _add_company(session, name, **overrides):
    fields = dict(
        company_name=name, country="South Africa", source_type="PRIVATE",
        careers_url="https://careers.example/jobs", active=True,
    )
    fields.update(overrides)
    company = Company(**fields)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def _add_role(session, company, title, **overrides):
    source = session.query(VacancySource).filter(VacancySource.company_id == company.id).first()
    if source is None:
        source = VacancySource(company_id=company.id, url=company.careers_url or "https://careers.example/jobs", ats_type="static")
        session.add(source)
        session.commit()
        session.refresh(source)
    now = datetime.now(timezone.utc)
    fields = dict(
        company_id=company.id, source_id=source.id, title=title, content_hash=f"hash-{title}",
        is_open=True, first_seen_at=now, last_seen_at=now, location="Johannesburg",
        description="secret advert body",
        application_url=f"https://careers.example/jobs/{title}",
    )
    fields.update(overrides)
    role = Vacancy(**fields)
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def test_public_page_hides_notes_and_lists_open_roles(client, db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        now = datetime.now(timezone.utc)
        linked = _add_company(
            s, "Mediclinic Southern Africa", source_type="HOSPITAL",
            careers_url="https://careers.mediclinic.example/jobs",
            notes="internal secret. careers_scope=global. do not publish",
            url_looks_like_careers=True, last_checked=now,
        )
        blank = _add_company(s, "Blank Hospital", source_type="HOSPITAL", careers_url=None, notes="also secret")
        inactive = _add_company(s, "Closed Board", careers_url="https://closed.example/careers", active=False)
        kenya = _add_company(s, "Nairobi Works", country="Kenya", careers_url="https://nairobi.example/careers")
        _add_role(
            s, linked, "Professional Nurse", province="Gauteng",
            application_url="https://careers.mediclinic.example/jobs/nurse",
        )
        closed = _add_role(s, linked, "Closed Nurse")
        closed.closing_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        closed.is_open = True
        s.commit()
        linked_id = linked.id
        blank_id = blank.id
        inactive_id = inactive.id
        kenya_name = kenya.company_name
    finally:
        s.close()

    page = client.get(f"/api/v1/employers/{linked_id}")
    assert page.status_code == 200, page.text
    body = page.json()
    assert body["careers_scope"] == "global"
    assert body["careers_url"].endswith("/jobs")
    assert body["url_looks_like_careers"] is True
    assert body["last_checked"]
    assert body["open_role_count"] == 1
    assert body["roles"][0]["title"] == "Professional Nurse"
    assert body["roles"][0]["company_id"] == linked_id
    assert body["roles"][0]["application_url"].endswith("/nurse")
    assert "description" not in body["roles"][0]
    assert "secret" not in page.text
    assert "notes" not in body

    assert client.get(f"/api/v1/employers/{blank_id}").status_code == 404
    assert client.get(f"/api/v1/employers/{inactive_id}").status_code == 404
    missing = client.get("/api/v1/employers/does-not-exist")
    assert missing.status_code == 404
    assert "secret" not in missing.text

    listed = client.get("/api/v1/employers", params={"limit": 10})
    assert listed.status_code == 200
    names = [row["company_name"] for row in listed.json()["employers"]]
    assert names[0] == "Mediclinic Southern Africa"
    assert "Nairobi Works" in names
    assert "Blank Hospital" not in names
    assert "Closed Board" not in names
    assert "secret" not in listed.text
    assert kenya_name == "Nairobi Works"
