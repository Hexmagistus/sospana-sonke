"""Expired opportunities stay stored and leave every public surface."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.migrations.opportunity_expiry import downgrade, upgrade
from app.models.company import Company
from app.models.organisation import EmployerEntitlement
from app.models.role_alert import RoleAlert
from app.models.vacancy import Vacancy, VacancySource
from app.services.daily_digest import _open_vacancy_rows
from app.services.intelligence_search import answer_question
from app.services.opportunity_expiry import sa_today, stamp_expired
from app.services.role_alerts import open_matches
from app.services.vacancy_counts import open_vacancy_counts
from tests.conftest import make_admin, register_and_login


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed(db_engine):
    session = sessionmaker(bind=db_engine)()
    now = datetime.now(timezone.utc)
    today = sa_today(now)
    try:
        company = Company(
            company_name="Ward Hospital",
            country="South Africa",
            source_type="HOSPITAL",
            careers_url="https://ward.example/careers",
            active=True,
        )
        session.add(company)
        session.commit()
        source = VacancySource(company_id=company.id, url="https://ward.example/careers", ats_type="static", active=True)
        session.add(source)
        session.commit()
        live = Vacancy(
            company_id=company.id, source_id=source.id, title="Live Nurse",
            content_hash="live", is_open=True, status="active", lifecycle_status="ACTIVE",
            closing_date=today + timedelta(days=1), country="South Africa", province="Gauteng",
            first_seen_at=now, last_seen_at=now, opportunity_type="job",
            description="A nurse post that is still open.",
        )
        dated = Vacancy(
            company_id=company.id, source_id=source.id, title="Expired Nurse",
            content_hash="dated", is_open=True, status="active", lifecycle_status="ACTIVE",
            closing_date=today - timedelta(days=1), country="South Africa", province="Gauteng",
            first_seen_at=now, last_seen_at=now, opportunity_type="job",
        )
        gone = Vacancy(
            company_id=company.id, source_id=source.id, title="Gone Nurse",
            content_hash="gone", is_open=False, status="active", lifecycle_status="REMOVED",
            country="South Africa", first_seen_at=now, last_seen_at=now, opportunity_type="learnership",
        )
        session.add_all([live, dated, gone])
        session.commit()
        session.add(EmployerEntitlement(
            account_id="featured-account",
            plan_code="featured",
            status="active",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=6),
            vacancy_id=dated.id,
        ))
        session.commit()
        return {
            "company_id": company.id,
            "live_id": live.id,
            "dated_id": dated.id,
            "gone_id": gone.id,
        }
    finally:
        session.close()


def test_public_surfaces_hide_expired_rows_and_admin_can_filter_them(client, db_engine):
    ids = _seed(db_engine)
    _, tokens = register_and_login(client)

    listed = client.get("/api/v1/jobs", params={"q": "Nurse"})
    assert listed.status_code == 200, listed.text
    found = {row["id"] for row in listed.json()["jobs"]}
    assert ids["live_id"] in found
    assert ids["dated_id"] not in found
    assert ids["gone_id"] not in found
    assert listed.json()["sponsored"] == []

    counts = client.get("/api/v1/jobs/counts").json()["counts"]
    assert counts["job"] == 1
    assert counts["learnership"] == 0

    sitemap = client.get("/api/v1/jobs/ids").json()
    assert ids["live_id"] in sitemap["ids"]
    assert ids["dated_id"] not in sitemap["ids"]
    assert ids["gone_id"] not in sitemap["ids"]

    suggest = client.get("/api/v1/jobs/suggest", params={"q": "Liv"}).json()
    assert suggest["titles"] == ["Live Nurse"]
    hidden_suggest = client.get("/api/v1/jobs/suggest", params={"q": "Exp"}).json()
    assert hidden_suggest["titles"] == []

    facets = client.get("/api/v1/jobs/facets").json()
    assert facets["countries"] == [{"name": "South Africa", "count": 1}]

    employer = client.get(f"/api/v1/employers/{ids['company_id']}")
    assert employer.status_code == 200, employer.text
    body = employer.json()
    assert body["open_role_count"] == 1
    assert [row["id"] for row in body["roles"]] == [ids["live_id"]]

    directory = client.get("/api/v1/companies/facets", headers=_auth(tokens)).json()
    assert directory["country_open_vacancies"]["South Africa"] == 1

    intel = sessionmaker(bind=db_engine)()
    try:
        answer = answer_question(intel, "Nursing jobs in South Africa")
    finally:
        intel.close()
    assert {row["id"] for row in answer.vacancies} == {ids["live_id"]}
    assert answer.vacancy_count == 1

    session = sessionmaker(bind=db_engine)()
    try:
        assert open_vacancy_counts(session, [ids["company_id"]]) == {ids["company_id"]: 1}
        from app.api.routes_career import _open_vacancy_count
        assert _open_vacancy_count(session, "Nurse") == 1
        window_end = datetime.now(timezone.utc) + timedelta(minutes=1)
        digest_ids = {row.id for row, _company in _open_vacancy_rows(session, window_end - timedelta(hours=1), window_end).all()}
        assert digest_ids == {ids["live_id"]}
        alert = RoleAlert(user_id="candidate", keyword="Nurse", active=True)
        matched = {row.id for row, _company in open_matches(session, [alert])}
        assert matched == {ids["live_id"]}
        stamped = stamp_expired(session)
        assert stamped == 1
        dated = session.get(Vacancy, ids["dated_id"])
        gone = session.get(Vacancy, ids["gone_id"])
        live = session.get(Vacancy, ids["live_id"])
        assert dated.status == "expired" and dated.expired_at is not None and dated.is_open is False
        assert gone.status == "expired" and gone.lifecycle_status == "REMOVED"
        assert live.status == "active" and live.expired_at is None
        assert session.query(Vacancy).count() == 3
    finally:
        session.close()

    dated_page = client.get(f"/api/v1/jobs/{ids['dated_id']}")
    assert dated_page.status_code == 410
    assert dated_page.json()["detail"] == "This opportunity has closed."
    assert "noindex" in dated_page.headers.get("x-robots-tag", "")
    gone_page = client.get(f"/api/v1/jobs/{ids['gone_id']}")
    assert gone_page.status_code == 410
    assert client.get("/api/v1/jobs/does-not-exist").status_code == 404

    hidden = client.get(f"/api/v1/vacancies/{ids['dated_id']}", headers=_auth(tokens))
    assert hidden.status_code == 410

    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    expired_list = client.get("/api/v1/admin/vacancies", params={"status": "expired"}, headers=_auth(admin))
    assert expired_list.status_code == 200, expired_list.text
    payload = expired_list.json()
    assert payload["active"] == 1
    assert payload["expired"] == 2
    assert {row["id"] for row in payload["rows"]} == {ids["dated_id"], ids["gone_id"]}
    assert {row["status"] for row in payload["rows"]} == {"expired"}
    active_list = client.get("/api/v1/admin/vacancies", params={"status": "active"}, headers=_auth(admin)).json()
    assert [row["id"] for row in active_list["rows"]] == [ids["live_id"]]
    kept = client.get(f"/api/v1/vacancies/{ids['dated_id']}", headers=_auth(admin))
    assert kept.status_code == 200
    assert kept.json()["status"] == "expired"


def test_downgrade_drops_expiry_columns_and_keeps_the_row():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    company = Company(company_name="Kept", country="South Africa", active=True)
    session.add(company)
    session.commit()
    source = VacancySource(company_id=company.id, url="https://kept.example/jobs", ats_type="static")
    session.add(source)
    session.commit()
    row = Vacancy(
        company_id=company.id, source_id=source.id, title="Kept Nurse", content_hash="kept",
        is_open=True, closing_date=date.today() - timedelta(days=2),
        first_seen_at=now, last_seen_at=now,
    )
    session.add(row)
    session.commit()
    row_id = row.id
    session.close()

    upgrade(engine)
    session = sessionmaker(bind=engine)()
    stamped = session.get(Vacancy, row_id)
    assert stamped.status == "expired"
    assert stamped.expired_at is not None
    assert session.query(Vacancy).count() == 1
    session.close()

    downgrade(engine)
    names = {col["name"] for col in inspect(engine).get_columns("vacancies")}
    assert "status" not in names
    assert "expired_at" not in names
    with engine.connect() as conn:
        title = conn.execute(text("SELECT title FROM vacancies")).scalar()
    assert title == "Kept Nurse"

    upgrade(engine)
    session = sessionmaker(bind=engine)()
    again = session.get(Vacancy, row_id)
    assert again.title == "Kept Nurse"
    assert again.status == "expired"
    session.close()
