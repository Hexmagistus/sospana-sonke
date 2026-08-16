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
