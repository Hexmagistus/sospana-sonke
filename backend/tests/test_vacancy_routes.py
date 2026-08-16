"""Route-level tests for scanning and vacancy listing (access control + basics)."""
from tests.conftest import register_and_login, make_admin
from app.models.company import Company
from app.models.vacancy import Vacancy
from datetime import datetime, timezone


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed_vacancy(db_engine, company_name="Acme"):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        c = Company(company_name=company_name, careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="src-x", title="Operations Manager",
                    location="Johannesburg", content_hash="hash1", is_open=True,
                    first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        return c.id, v.id
    finally:
        s.close()


def test_scan_requires_admin(client, db_engine):
    _, tokens = register_and_login(client)  # candidate
    company_id, _ = _seed_vacancy(db_engine)
    r = client.post(f"/api/v1/companies/{company_id}/scan", headers=_auth(tokens))
    assert r.status_code == 403


def test_scan_missing_company(client, db_engine):
    email, password = make_admin(db_engine)
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    r = client.post("/api/v1/companies/does-not-exist/scan", headers=_auth(tokens))
    assert r.status_code == 404


def test_list_vacancies_requires_auth(client, db_engine):
    _seed_vacancy(db_engine)
    assert client.get("/api/v1/vacancies").status_code in (401, 403)


def test_list_and_get_vacancy(client, db_engine):
    _, tokens = register_and_login(client)
    company_id, vac_id = _seed_vacancy(db_engine)

    listed = client.get("/api/v1/vacancies", headers=_auth(tokens)).json()
    assert any(v["id"] == vac_id for v in listed)

    search = client.get("/api/v1/vacancies", params={"q": "operations"}, headers=_auth(tokens)).json()
    assert len(search) == 1

    detail = client.get(f"/api/v1/vacancies/{vac_id}", headers=_auth(tokens))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Operations Manager"
    assert "requirements" in detail.json()

    by_company = client.get(f"/api/v1/companies/{company_id}/vacancies", headers=_auth(tokens)).json()
    assert len(by_company) == 1
