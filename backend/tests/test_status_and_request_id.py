"""Request ids, the access line, and the public status checks."""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.core.request_id import access_line, request_id_from
from app.models.company import Company
from app.models.notification import JobRun
from app.models.scan_log import ScanLog
from app.models.vacancy import VacancySource
from app.services.status_report import STALE_AFTER_MINUTES, status_report


NOW = datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)


def test_request_id_keeps_a_safe_token_and_mints_the_rest():
    assert request_id_from("abc12345") == "abc12345"
    assert request_id_from("  trace_id-1 ") == "trace_id-1"
    minted = request_id_from("no")
    assert len(minted) == 32
    assert request_id_from("spaces not ok") != "spaces not ok"
    line = access_line("abc12345", "GET", "/api/v1/auth/verify", 200, 12.5)
    payload = json.loads(line)
    assert payload["request_id"] == "abc12345"
    assert payload["path"] == "/api/v1/auth/verify"
    assert "token" not in line
    secret = access_line("abc12345", "GET", "/api/v1/auth/verify", 200, 1)
    assert json.loads(secret)["path"].startswith("/api")


def test_health_echoes_the_request_id(client, caplog):
    caplog.set_level(logging.INFO, logger="app.access")
    response = client.get("/health", headers={"X-Request-ID": "trace-1234"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "trace-1234"
    assert any("trace-1234" in rec.message and '"path":"/health"' in rec.message for rec in caplog.records)
    weird = client.get("/health", headers={"X-Request-ID": "bad id"})
    assert len(weird.headers["x-request-id"]) == 32
    caplog.clear()
    client.get("/health?token=supersecretvalue")
    access = [rec for rec in caplog.records if rec.name == "app.access"]
    assert access
    assert all("supersecretvalue" not in rec.message and "token=" not in rec.message for rec in access)


def test_status_reports_a_live_database_and_a_fresh_scan(client, db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        company = Company(company_name="Status Co", country="South Africa", active=True)
        s.add(company)
        s.commit()
        source = VacancySource(
            company_id=company.id, url="https://status.example/jobs", ats_type="static",
            active=True, consecutive_failures=3,
        )
        s.add(source)
        s.commit()
        fresh = datetime.now(timezone.utc) - timedelta(minutes=20)
        s.add(ScanLog(
            company_id=company.id, source_id=source.id, url=source.url, status="success",
            finished_at=fresh,
        ))
        s.add(JobRun(
            job_name="scan_due_companies", status="success",
            started_at=fresh - timedelta(minutes=1), finished_at=fresh,
        ))
        s.commit()
    finally:
        s.close()

    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert "s-maxage=600" in response.headers["cache-control"]
    body = response.json()
    assert body["components"]["database"]["status"] == "ok"
    assert body["components"]["api"]["status"] == "ok"
    scanner = body["components"]["scanner"]
    assert scanner["schedule_minutes"] == 15
    assert scanner["stale_after_minutes"] == STALE_AFTER_MINUTES == 120
    assert scanner["sources_at_failure_threshold"] == 1
    assert scanner["status"] == "ok"
    assert body["status"] == "degraded"
    assert "postgres://" not in response.text


def test_status_marks_an_old_scan_stale(db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        company = Company(company_name="Old Scan", country="South Africa", active=True)
        s.add(company)
        s.commit()
        s.add(ScanLog(
            company_id=company.id, status="success",
            finished_at=NOW - timedelta(minutes=STALE_AFTER_MINUTES + 5),
        ))
        s.commit()
        body = status_report(s, now=NOW)
    finally:
        s.close()
    assert body["components"]["scanner"]["status"] == "stale"
    assert body["status"] == "degraded"


def test_status_with_no_scan_is_not_a_database_failure(db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        body = status_report(s, now=NOW)
    finally:
        s.close()
    assert body["components"]["database"]["status"] == "ok"
    assert body["components"]["scanner"]["status"] == "no_scans"
    assert body["components"]["scanner"]["latest_finished_at"] is None
    assert body["status"] == "degraded"
