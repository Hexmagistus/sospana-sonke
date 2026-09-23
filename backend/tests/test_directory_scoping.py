"""Server-side directory scoping (anti bulk-copy) + facets + surprise."""
import uuid

from app.api import routes_companies
from tests.conftest import register_and_login, make_admin


def _seed(db_engine, n_sa=5, n_bw=3):
    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company
    db = sessionmaker(bind=db_engine)()
    for country, n in (("South Africa", n_sa), ("Botswana", n_bw)):
        for i in range(n):
            db.add(Company(id=str(uuid.uuid4()), company_name=f"{country} Co {i}", country=country,
                           source_type="SOE" if i % 2 else "PRIVATE", active=True,
                           careers_url=f"https://example.com/{country[:2]}{i}/careers" if i % 3 else None))
    db.commit(); db.close()


def _h(client, email="thandi@example.com"):
    _, tok = register_and_login(client, email=email)
    return {"Authorization": f"Bearer {tok['access_token']}"}


def test_unscoped_user_request_is_capped(client, db_engine, monkeypatch):
    _seed(db_engine)
    monkeypatch.setattr(routes_companies, "_UNSCOPED_USER_MAX_ROWS", 4)
    rows = client.get("/api/v1/companies?limit=5000", headers=_h(client)).json()
    assert len(rows) == 4


def test_scoped_by_country_returns_that_country_only(client, db_engine):
    _seed(db_engine)
    rows = client.get("/api/v1/companies?country=Botswana&limit=1500", headers=_h(client)).json()
    assert len(rows) == 3 and {r["country"] for r in rows} == {"Botswana"}


def test_search_and_ids(client, db_engine):
    _seed(db_engine)
    h = _h(client)
    hits = client.get("/api/v1/companies?q=africa co 1", headers=h).json()
    assert [r["company_name"] for r in hits] == ["South Africa Co 1"]
    wanted = [hits[0]["id"]]
    got = client.get(f"/api/v1/companies?ids={','.join(wanted)}", headers=h).json()
    assert [r["id"] for r in got] == wanted
    # LIKE wildcards in user input are neutralised, not interpreted.
    assert client.get("/api/v1/companies?q=%25", headers=h).json() == []


def test_admin_keeps_full_listing(client, db_engine, monkeypatch):
    _seed(db_engine)
    monkeypatch.setattr(routes_companies, "_UNSCOPED_USER_MAX_ROWS", 2)
    email, pw = make_admin(db_engine)
    tok = client.post("/api/v1/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    rows = client.get("/api/v1/companies?limit=5000", headers={"Authorization": f"Bearer {tok}"}).json()
    assert len(rows) == 8


def test_facets_counts_without_rows(client, db_engine):
    _seed(db_engine)
    f = client.get("/api/v1/companies/facets", headers=_h(client)).json()
    assert f["total"] == 8
    assert f["country_counts"] == {"South Africa": 5, "Botswana": 3}
    assert f["country_with_links"]["South Africa"] == 3   # i = 1, 2, 4
    assert f["type_counts"]["SOE"] + f["type_counts"]["PRIVATE"] == 8


def test_surprise_returns_one_with_link(client, db_engine):
    _seed(db_engine)
    c = client.get("/api/v1/companies/surprise", headers=_h(client)).json()
    assert c["careers_url"]
