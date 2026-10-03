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


def test_icon_miss_is_a_cacheable_204_and_never_fetches(client, db_engine, monkeypatch):
    company_id, tokens = _seed_one_company(client, db_engine)

    def boom(*a, **k):
        raise AssertionError("a page view must never reach out to the web")

    monkeypatch.setattr("app.services.logo_service.fetch_company_icon", boom)
    r = client.get(f"/api/v1/companies/{company_id}/icon", follow_redirects=False)
    assert r.status_code == 204
    assert r.headers["cache-control"] == "public, max-age=86400"

    listed = client.get("/api/v1/companies?country=South%20Africa", headers=_auth_header(tokens)).json()
    row = next(c for c in listed if c["id"] == company_id)
    assert row["has_icon"] is False
    assert "favicon_url" not in row and "favicon_data" not in row

    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company
    db = sessionmaker(bind=db_engine)()
    db.get(Company, company_id).favicon_url = "https://careers.goldfields.com/logo.png"
    db.commit()
    r = client.get(f"/api/v1/companies/{company_id}/icon", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "https://careers.goldfields.com/logo.png"
    listed = client.get("/api/v1/companies?country=South%20Africa", headers=_auth_header(tokens)).json()
    assert next(c for c in listed if c["id"] == company_id)["has_icon"] is True

    # Stored bytes alone (no URL) also count as "has an icon".
    c = db.get(Company, company_id)
    c.favicon_url, c.favicon_data, c.favicon_mime = None, b"\x89PNG\r\n\x1a\n", "image/png"
    db.commit()
    db.close()
    listed = client.get("/api/v1/companies?country=South%20Africa", headers=_auth_header(tokens)).json()
    assert next(c for c in listed if c["id"] == company_id)["has_icon"] is True


def test_icon_404_for_unknown_company(client, db_engine):
    r = client.get("/api/v1/companies/does-not-exist/icon", follow_redirects=False)
    assert r.status_code == 404


def test_import_marks_researched_links_live_and_keeps_tester_verdict(db):
    from app.models.company import Company
    from app.services.csv_import import import_companies_from_csv

    head = "company_name,jse_code,careers_url,careers_status,scraping_status,active,country,source_type\n"
    first = head + (
        "Verified Co,,https://verified.example/careers,green_verified,pending,true,South Africa,PRIVATE\n"
        "Fallback Co,,https://fallback.example/,amber_company_route,pending,true,South Africa,PRIVATE\n"
    )
    import_companies_from_csv(db, first.encode())
    status = {c.company_name: c.scraping_status for c in db.query(Company).all()}
    assert status["Verified Co"] == "ok"
    assert status["Fallback Co"] == "pending"

    # The URL tester later marks Fallback Co ok; a boot-time re-import must not undo it.
    fb = db.query(Company).filter(Company.company_name == "Fallback Co").one()
    fb.scraping_status = "ok"
    db.commit()
    import_companies_from_csv(db, first.encode())
    db.expire_all()
    assert db.query(Company).filter(Company.company_name == "Fallback Co").one().scraping_status == "ok"


def test_import_caps_scraping_status_so_bootstrap_does_not_abort(db):
    """Postgres rejects scraping_status longer than varchar(30) and rolls the
    whole seed import back. A prose status must be stored short, not raised."""
    from app.models.company import Company
    from app.services.csv_import import import_companies_from_csv

    prose = "Live-fetched; vacancies page confirmed working (currently no open postings)"
    assert len(prose) > 30
    head = "company_name,jse_code,careers_url,careers_status,scraping_status,active,country,source_type\n"
    body = head + (
        f'Long Status Co,,https://example.edu/vacancies,grey_none_verified,"{prose}",true,Seychelles,COLLEGE\n'
    )
    result = import_companies_from_csv(db, body.encode())
    assert result.errors == []
    assert result.created == 1
    row = db.query(Company).filter(Company.company_name == "Long Status Co").one()
    assert len(row.scraping_status) <= 30
    assert row.scraping_status == "needs_review"


def test_import_keeps_same_name_in_different_countries(db):
    """A blank later row in one country must not wipe the verified URL of the
    same employer name in another country."""
    from app.models.company import Company
    from app.services.csv_import import import_companies_from_csv

    head = "company_name,jse_code,careers_url,careers_status,scraping_status,active,country,source_type\n"
    body = head + (
        "Human Resource Development Council (HRDC),,https://www.hrdc.org.bw/vacancies,green_verified,pending,true,Botswana,SETA\n"
        "Human Resource Development Council (HRDC),,,grey_none_verified,no_url,true,Mauritius,SETA\n"
    )
    result = import_companies_from_csv(db, body.encode())
    assert result.created == 2
    rows = db.query(Company).filter(Company.company_name.startswith("Human Resource")).all()
    by_country = {c.country: c for c in rows}
    assert set(by_country) == {"Botswana", "Mauritius"}
    assert by_country["Botswana"].careers_url == "https://www.hrdc.org.bw/vacancies"
    assert by_country["Mauritius"].careers_url is None
