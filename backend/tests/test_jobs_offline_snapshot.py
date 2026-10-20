"""The jobs list survives a database outage and never shows an expired role."""
import json
from datetime import date

from sqlalchemy.exc import OperationalError

from app.api import routes_vacancies
from app.services import jobs_snapshot
from tests.test_vacancy_routes import _seed_vacancy


def _boom(*args, **kwargs):
    raise OperationalError("SELECT 1", {}, Exception("402 quota exceeded"))


def test_unexpired_drops_past_closing_dates():
    jobs = [{"id": "a", "closing_date": "2026-10-19"}, {"id": "b", "closing_date": "2026-10-20"},
            {"id": "c", "closing_date": None}, {"id": "d", "closing_date": "2027-01-01", "is_open": False}]
    kept = [j["id"] for j in jobs_snapshot.unexpired(jobs, today=date(2026, 10, 20))]
    assert kept == ["b", "c"]


def test_baked_bootstrap_is_valid_and_open_in_2026():
    data = json.loads(jobs_snapshot.BAKED.read_text())
    assert len(data["jobs"]) == 8
    assert all(j["application_url"].startswith("https://") for j in data["jobs"])
    after = jobs_snapshot.unexpired(data["jobs"], today=date(2026, 10, 28))
    assert {j["company_name"] for j in after} >= {"MANCOSA x SPAR", "ATNS"}
    assert "CHIETA" not in {j["company_name"] for j in after}


def test_db_error_serves_snapshot_not_500(client, monkeypatch, tmp_path):
    monkeypatch.setattr(jobs_snapshot, "RUNTIME", tmp_path / "none.json")
    monkeypatch.setattr(routes_vacancies, "_query_public_jobs", _boom)
    r = client.get("/api/v1/jobs")
    assert r.status_code == 200
    body = r.json()
    assert body["from_snapshot"] is True
    assert r.headers["X-Jobs-Source"] == "snapshot"
    today = jobs_snapshot.sa_today().isoformat()
    assert all((j["closing_date"] or "9999") >= today for j in body["jobs"])


def test_success_saves_snapshot_then_outage_uses_it(client, db_engine, monkeypatch, tmp_path):
    runtime = tmp_path / "snap.json"
    monkeypatch.setattr(jobs_snapshot, "RUNTIME", runtime)
    _seed_vacancy(db_engine)
    r = client.get("/api/v1/jobs")
    assert r.status_code == 200 and r.json()["from_snapshot"] is False
    assert "s-maxage=600" in r.headers["Cache-Control"]
    assert runtime.exists()
    monkeypatch.setattr(routes_vacancies, "_query_public_jobs", _boom)
    r = client.get("/api/v1/jobs")
    assert [j["title"] for j in r.json()["jobs"]] == ["Operations Manager"]


def test_status_survives_db_error(client, monkeypatch):
    import app.services.status_report as sr
    monkeypatch.setattr(sr, "status_report", _boom)
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    assert r.json()["components"]["database"]["status"] == "down"
