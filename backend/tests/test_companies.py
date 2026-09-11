"""Tests for the company database, CSV import, and admin gating."""
import io

from tests.conftest import register_and_login, make_admin

CSV = (
    "company_name,jse_code,careers_url,source_type,scraping_status,active,relevance_note,country\n"
    "Gold Fields,GFI,https://careers.goldfields.com/,JSE,pending,true,Mining,South Africa\n"
    "Airports Company South Africa,,,SOE,no_url,false,SOE,South Africa\n"
    "Gold Fields,GFI,https://careers.goldfields.com/jobs,JSE,pending,true,Mining updated,South Africa\n"
)


def _auth_header(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_import_requires_admin(client):
    _, tokens = register_and_login(client)  # ordinary candidate
    files = {"file": ("companies.csv", io.BytesIO(CSV.encode()), "text/csv")}
    r = client.post("/api/v1/companies/import", files=files, headers=_auth_header(tokens))
    assert r.status_code == 403


def test_admin_import_dedupes(client, db_engine):
    email, password = make_admin(db_engine)
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    files = {"file": ("companies.csv", io.BytesIO(CSV.encode()), "text/csv")}
    r = client.post("/api/v1/companies/import", files=files, headers=_auth_header(tokens))
    assert r.status_code == 200, r.text
    body = r.json()
    # Three rows: two Gold Fields (same name+code) collapse to one; ACSA is separate.
    assert body["created"] == 2
    assert body["updated"] == 1
    assert body["total_rows"] == 3

    listed = client.get("/api/v1/companies", headers=_auth_header(tokens)).json()
    names = sorted(c["company_name"] for c in listed)
    assert names == ["Airports Company South Africa", "Gold Fields"]
    gf = next(c for c in listed if c["company_name"] == "Gold Fields")
    assert gf["careers_url"] == "https://careers.goldfields.com/jobs"  # updated in place


def test_list_filters_by_source_type(client, db_engine):
    email, password = make_admin(db_engine)
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    files = {"file": ("companies.csv", io.BytesIO(CSV.encode()), "text/csv")}
    client.post("/api/v1/companies/import", files=files, headers=_auth_header(tokens))
    soe = client.get("/api/v1/companies", params={"source_type": "SOE"}, headers=_auth_header(tokens)).json()
    assert len(soe) == 1 and soe[0]["source_type"] == "SOE"


def test_reject_non_csv(client, db_engine):
    email, password = make_admin(db_engine)
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    files = {"file": ("companies.txt", io.BytesIO(b"nope"), "text/plain")}
    r = client.post("/api/v1/companies/import", files=files, headers=_auth_header(tokens))
    assert r.status_code == 400


def _seed_one_company(client, db_engine, **overrides):
    """Import one company via the admin CSV route and return its id."""
    row = {
        "company_name": "Gold Fields", "jse_code": "GFI",
        "careers_url": "https://careers.goldfields.com/", "source_type": "JSE",
        "scraping_status": "pending", "active": "true", "relevance_note": "Mining",
        "country": "South Africa",
    }
    row.update(overrides)
    csv_text = ",".join(row.keys()) + "\n" + ",".join(row.values()) + "\n"
    email, password = make_admin(db_engine, email="admin2@example.com")
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    files = {"file": ("companies.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    client.post("/api/v1/companies/import", files=files, headers=_auth_header(tokens))
    listed = client.get("/api/v1/companies", headers=_auth_header(tokens)).json()
    return next(c for c in listed if c["company_name"] == row["company_name"])["id"], tokens


def test_icon_redirects_to_discovered_favicon(client, db_engine, monkeypatch):
    company_id, _ = _seed_one_company(client, db_engine)

    async def fake_discover(website, careers_url, client=None):
        return "https://careers.goldfields.com/logo.png"

    monkeypatch.setattr("app.api.routes_companies.discover_favicon", fake_discover)
    r = client.get(f"/api/v1/companies/{company_id}/icon", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "https://careers.goldfields.com/logo.png"


def test_icon_404_when_nothing_found(client, db_engine, monkeypatch):
    company_id, _ = _seed_one_company(client, db_engine)

    async def fake_discover(website, careers_url, client=None):
        return None

    monkeypatch.setattr("app.api.routes_companies.discover_favicon", fake_discover)
    r = client.get(f"/api/v1/companies/{company_id}/icon", follow_redirects=False)
    assert r.status_code == 404


def test_icon_404_for_unknown_company(client, db_engine):
    r = client.get("/api/v1/companies/does-not-exist/icon", follow_redirects=False)
    assert r.status_code == 404


def test_icon_result_cached_not_refetched(client, db_engine, monkeypatch):
    company_id, _ = _seed_one_company(client, db_engine)
    calls = {"n": 0}

    async def fake_discover(website, careers_url, client=None):
        calls["n"] += 1
        return "https://careers.goldfields.com/logo.png"

    monkeypatch.setattr("app.api.routes_companies.discover_favicon", fake_discover)
    client.get(f"/api/v1/companies/{company_id}/icon", follow_redirects=False)
    client.get(f"/api/v1/companies/{company_id}/icon", follow_redirects=False)
    # Second request is served from the cached favicon_url — discovery ran once.
    assert calls["n"] == 1
