"""Tests for POST /companies/{id}/report-link, its admin listing, and the
GET /companies/coverage rollup."""
import io

from tests.conftest import register_and_login, make_admin

CSV = (
    "company_name,jse_code,careers_url,source_type,scraping_status,active,relevance_note,country\n"
    "Gold Fields,GFI,https://careers.goldfields.com/,JSE,ok,true,Mining,South Africa\n"
    "University of Somewhere,,https://uni.example/careers,UNI,pending,true,Uni,Zambia\n"
    "University of Nowhere,,https://uni2.example/,UNI,needs_review,true,Uni,Zambia\n"
    "Broken Co,,https://dead.example/,SOE,no_url,false,Dead,South Africa\n"
)


def _auth_header(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed(client, db_engine):
    email, password = make_admin(db_engine)
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    files = {"file": ("companies.csv", io.BytesIO(CSV.encode()), "text/csv")}
    client.post("/api/v1/companies/import", files=files, headers=_auth_header(tokens))
    listed = client.get("/api/v1/companies", headers=_auth_header(tokens)).json()
    return {c["company_name"]: c["id"] for c in listed}, tokens


def test_report_link_requires_valid_reason(client, db_engine):
    ids, tokens = _seed(client, db_engine)
    r = client.post(f"/api/v1/companies/{ids['Gold Fields']}/report-link", json={"reason": "x"},
                    headers=_auth_header(tokens))
    assert r.status_code == 422  # below min_length=3


def test_report_link_creates_a_report(client, db_engine):
    ids, tokens = _seed(client, db_engine)
    r = client.post(f"/api/v1/companies/{ids['Gold Fields']}/report-link",
                    json={"reason": "This redirects to an unrelated site."},
                    headers=_auth_header(tokens))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "open"
    assert body["company_id"] == ids["Gold Fields"]


def test_report_link_unknown_company_404s(client, db_engine):
    _, tokens = _seed(client, db_engine)
    r = client.post("/api/v1/companies/does-not-exist/report-link",
                    json={"reason": "Broken link"}, headers=_auth_header(tokens))
    assert r.status_code == 404


def test_link_reports_listing_is_admin_only(client, db_engine):
    ids, admin_tokens = _seed(client, db_engine)
    client.post(f"/api/v1/companies/{ids['Gold Fields']}/report-link",
               json={"reason": "Broken link"}, headers=_auth_header(admin_tokens))

    _, candidate_tokens = register_and_login(client, email="candidate@example.com")
    r = client.get("/api/v1/companies/link-reports", headers=_auth_header(candidate_tokens))
    assert r.status_code == 403

    r = client.get("/api/v1/companies/link-reports", headers=_auth_header(admin_tokens))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_coverage_map_buckets_by_country_and_category(client, db_engine):
    _, tokens = _seed(client, db_engine)
    r = client.get("/api/v1/companies/coverage", headers=_auth_header(tokens))
    assert r.status_code == 200
    rows = {(row["country"], row["source_type"]): row for row in r.json()}

    za_jse = rows[("South Africa", "JSE")]
    assert za_jse["total"] == 1 and za_jse["verified_ok"] == 1

    za_soe = rows[("South Africa", "SOE")]
    assert za_soe["total"] == 1 and za_soe["needs_attention"] == 1 and za_soe["active"] == 0

    zm_uni = rows[("Zambia", "UNI")]
    assert zm_uni["total"] == 2
    assert zm_uni["pending_verification"] == 1
    assert zm_uni["needs_attention"] == 1
