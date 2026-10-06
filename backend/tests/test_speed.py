"""Free-tier speed pass: health metadata, public cache, scan time budget, pool shape."""
import json

import httpx
import pytest

from app.db.session import describe_database
from app.scraper.politeness import backoff_retry_cap, request_with_backoff
from tests.conftest import register_and_login


def test_health_reports_commit_and_db_shape(client, monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123deadbeef")
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["commit"] == "abc123deadbeef"
    assert body["db_pooled"] is False  # tests use sqlite
    assert body["db_region"] is None
    assert r.headers["cache-control"] == "no-store"


def test_describe_database_reads_pooler_and_region_without_secrets():
    url = "postgresql://user:s3cret@ep-example-pooler.us-west-2.aws.neon.tech/neondb?sslmode=require"
    info = describe_database(url)
    assert info == {"pooled": True, "region": "us-west-2"}
    direct = "postgres://user:s3cret@ep-example.us-east-1.aws.neon.tech/neondb"
    assert describe_database(direct) == {"pooled": False, "region": "us-east-1"}
    assert "s3cret" not in json.dumps(info)


def test_comments_summary_sends_etag_and_304(client):
    from app.db.session import get_db
    from app.models.company import Company

    db = next(client.app.dependency_overrides[get_db]())
    company = Company(company_name="Cache Co", country="South Africa", careers_url="https://cache.example/jobs")
    db.add(company)
    db.commit()
    cid = company.id
    _, tokens = register_and_login(client, email="cache@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    posted = client.post(f"/api/v1/companies/{cid}/comments", headers=headers, json={"kind": "works"})
    assert posted.status_code == 201

    first = client.get("/api/v1/comments/summary")
    assert first.status_code == 200
    assert first.json()[cid]["total"] == 1
    assert first.json()[cid]["works"] == 1
    assert first.json()[cid]["latest"]["kind"] == "works"
    assert "stale-while-revalidate" in first.headers["cache-control"]
    etag = first.headers["etag"]
    assert etag

    second = client.get("/api/v1/comments/summary", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""
    assert second.headers["etag"] == etag


def test_dashboard_is_private_cache(client):
    _, tokens = register_and_login(client, email="dash-cache@example.com")
    r = client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert r.headers["cache-control"].startswith("private")
    assert "stale-while-revalidate" in r.headers["cache-control"]
    # GZip middleware also adds Accept-Encoding. Authorization must be present
    # so a shared cache cannot reuse one person's dashboard for another.
    assert "Authorization" in r.headers["vary"]
    assert "total_matches" not in r.json()


def test_scan_due_does_not_start_a_company_without_time(db, monkeypatch):
    from app.models.company import Company
    from app.scheduler.jobs import scan_due_companies

    db.add(Company(company_name="Slow Co", careers_url="https://slow.example/careers", active=True))
    db.commit()
    calls = []

    def _fake(snapshot, client, now=None):
        calls.append(snapshot.url)
        raise AssertionError("no fetch should start without time")

    monkeypatch.setattr("app.services.scan_batch._default_fetch", _fake)
    out = scan_due_companies(db, limit=5, max_seconds=0)
    assert calls == []
    assert out["companies_scanned"] == 0
    assert out["stopped_early_on_time_budget"] is True


def test_backoff_cap_makes_a_single_attempt():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503)

    sleeps = []
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as c:
        with backoff_retry_cap(1):
            with pytest.raises(httpx.HTTPStatusError):
                request_with_backoff(c, "https://x.co.za/api", retries=3, sleep=sleeps.append)
    assert calls["n"] == 1
    assert sleeps == []
