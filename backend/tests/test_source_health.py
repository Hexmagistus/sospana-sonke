"""Admin source-health summary and the dashboard freshness stamp."""
from datetime import datetime, timezone

from tests.conftest import register_and_login, make_admin
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_source_health_is_admin_only_and_reports_the_latest_read(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    checked = datetime(2026, 9, 27, 8, 30, tzinfo=timezone.utc)
    seen = datetime(2026, 9, 27, 8, 15, tzinfo=timezone.utc)
    S = sessionmaker(bind=db_engine)
    db = S()
    try:
        company = Company(company_name="Takealot", country="South Africa",
                          careers_url="https://job-boards.greenhouse.io/takealotcom")
        db.add(company)
        db.commit()
        db.refresh(company)
        source = VacancySource(
            company_id=company.id, url=company.careers_url, ats_type="greenhouse",
            last_status="ok", last_checked=checked, last_vacancy_count=89,
            consecutive_failures=0,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        db.add(Vacancy(
            company_id=company.id, source_id=source.id, title="Retail Media Lead",
            content_hash="h-retail", is_open=True, first_seen_at=seen, last_seen_at=seen,
        ))
        db.commit()
    finally:
        db.close()

    _, tokens = register_and_login(client)
    assert client.get("/api/v1/admin/source-health", headers=_auth(tokens)).status_code == 403

    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    body = client.get("/api/v1/admin/source-health", headers=_auth(admin))
    assert body.status_code == 200, body.text
    health = body.json()
    assert health["sources"] == 1
    assert health["open_vacancies"] == 1
    assert health["by_status"]["ok"] == 1
    assert health["by_ats"]["greenhouse"] == 1
    assert health["recent"][0]["company_name"] == "Takealot"
    assert health["recent"][0]["last_vacancy_count"] == 89
    assert health["last_success_at"].startswith("2026-09-27T08:30")

    dash = client.get("/api/v1/dashboard", headers=_auth(tokens))
    assert dash.status_code == 200
    assert dash.json()["listings_updated_at"].startswith("2026-09-27T08:15")
    assert health["employers"] >= 1
    assert health["recent"][0]["source_id"]
    assert health["duplicates_prevented"] == 0

    logs = client.get("/api/v1/admin/scan-logs", headers=_auth(admin))
    assert logs.status_code == 200
    assert logs.json() == []
    assert client.get("/api/v1/admin/scan-logs", headers=_auth(tokens)).status_code == 403

    paused = client.post(
        f"/api/v1/admin/sources/{health['recent'][0]['source_id']}/active",
        json={"active": False}, headers=_auth(admin),
    )
    assert paused.status_code == 200
    assert paused.json()["active"] is False
    resumed = client.post(
        f"/api/v1/admin/sources/{health['recent'][0]['source_id']}/active",
        json={"active": True}, headers=_auth(admin),
    )
    assert resumed.status_code == 200
    assert resumed.json()["active"] is True
    again = client.get("/api/v1/admin/source-health", headers=_auth(admin)).json()
    assert again["recent"][0]["active"] is True
    assert again["recent"][0]["scraper_status"] is None
