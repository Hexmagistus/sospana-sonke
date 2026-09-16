"""Tests for trust/scam flagging, duplicate detection, and vacancy reporting."""
from datetime import datetime, timedelta, timezone

from tests.conftest import register_and_login, make_admin
from app.models.company import Company
from app.models.vacancy import Vacancy
from app.services.trust_service import scan_for_trust_flags
from app.services.duplicate_service import find_duplicate_groups, merge_duplicates


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---- trust_service -----------------------------------------------------------

def test_scan_for_trust_flags_payment_request():
    flags = scan_for_trust_flags(
        title="Data Capturer", description="A small registration fee is required to apply.",
        salary_min=None, salary_max=None, application_url="https://x.com/apply", source_url=None,
    )
    assert "payment_request" in flags


def test_scan_for_trust_flags_unrealistic_salary():
    flags = scan_for_trust_flags(
        title="General Worker", description="Entry level role.",
        salary_min=350000, salary_max=400000, application_url="https://x.com/apply", source_url=None,
    )
    assert "unrealistic_salary" in flags


def test_scan_for_trust_flags_missing_application_link():
    flags = scan_for_trust_flags(
        title="Cashier", description="Normal listing.",
        salary_min=8000, salary_max=10000, application_url=None, source_url=None,
    )
    assert "missing_application_link" in flags


def test_scan_for_trust_flags_clean_listing_has_no_flags():
    flags = scan_for_trust_flags(
        title="Process Controller", description="Requires a National Diploma and 2 years experience.",
        salary_min=15000, salary_max=20000, application_url="https://acme.com/careers/123", source_url=None,
    )
    assert flags == []


# ---- duplicate_service ---------------------------------------------------------

def _seed_two_near_identical(db_engine, company_name="Acme"):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        c = Company(company_name=company_name, careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        older = Vacancy(company_id=c.id, source_id="s1", title="Process Controller",
                        location="Vereeniging", content_hash="dup-h1", is_open=True,
                        first_seen_at=now - timedelta(days=5), last_seen_at=now)
        newer = Vacancy(company_id=c.id, source_id="s2", title="Process Controller!",  # punctuation differs
                        location="vereeniging", content_hash="dup-h2", is_open=True,
                        first_seen_at=now, last_seen_at=now)
        s.add_all([older, newer]); s.commit()
        s.refresh(older); s.refresh(newer)
        return c.id, older.id, newer.id
    finally:
        s.close()


def test_find_duplicate_groups_matches_normalized_title_and_location(db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    _, older_id, newer_id = _seed_two_near_identical(db_engine)
    groups = find_duplicate_groups(s)
    assert len(groups) == 1
    assert groups[0].keep.id == older_id  # oldest kept as canonical
    assert [d.id for d in groups[0].duplicates] == [newer_id]
    s.close()


def test_merge_duplicates_soft_closes_and_links(db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    _, keep_id, dup_id = _seed_two_near_identical(db_engine)
    merged = merge_duplicates(s, keep_id=keep_id, duplicate_ids=[dup_id])
    assert merged == 1
    dup = s.get(Vacancy, dup_id)
    assert dup.is_open is False
    assert dup.deleted_at is not None
    assert dup.duplicate_of_id == keep_id
    keep = s.get(Vacancy, keep_id)
    assert keep.is_open is True and keep.deleted_at is None  # canonical untouched
    s.close()


def test_merge_duplicates_refuses_cross_company(db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    now = datetime.now(timezone.utc)
    c1 = Company(company_name="Acme", careers_url="https://boards.greenhouse.io/acme")
    c2 = Company(company_name="Beta", careers_url="https://boards.greenhouse.io/beta")
    s.add_all([c1, c2]); s.commit(); s.refresh(c1); s.refresh(c2)
    v1 = Vacancy(company_id=c1.id, source_id="s1", title="Process Controller",
                content_hash="x1", is_open=True, first_seen_at=now, last_seen_at=now)
    v2 = Vacancy(company_id=c2.id, source_id="s2", title="Process Controller",
                content_hash="x2", is_open=True, first_seen_at=now, last_seen_at=now)
    s.add_all([v1, v2]); s.commit(); s.refresh(v1); s.refresh(v2)

    merged = merge_duplicates(s, keep_id=v1.id, duplicate_ids=[v2.id])
    assert merged == 0
    v2_after = s.get(Vacancy, v2.id)
    assert v2_after.is_open is True and v2_after.duplicate_of_id is None
    s.close()


# ---- routes ---------------------------------------------------------------

def _seed_vacancy(db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        c = Company(company_name="Acme", careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title="Process Controller",
                    content_hash="rpt-h1", is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        return v.id
    finally:
        s.close()


def test_report_vacancy_and_admin_listing(client, db_engine):
    _, tokens = register_and_login(client)
    vac_id = _seed_vacancy(db_engine)

    r = client.post(f"/api/v1/vacancies/{vac_id}/report", headers=_auth(tokens),
                    json={"category": "scam", "details": "Asked me to pay a fee."})
    assert r.status_code == 201, r.text
    assert r.json()["category"] == "scam"

    bad = client.post(f"/api/v1/vacancies/{vac_id}/report", headers=_auth(tokens),
                      json={"category": "not-a-real-category"})
    assert bad.status_code == 422

    email, password = make_admin(db_engine)
    admin_tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    listed = client.get("/api/v1/admin/vacancy-reports", headers=_auth(admin_tokens))
    assert listed.status_code == 200
    assert any(x["category"] == "scam" for x in listed.json())

    # A non-admin cannot see the triage queue.
    assert client.get("/api/v1/admin/vacancy-reports", headers=_auth(tokens)).status_code == 403


def test_admin_duplicate_endpoints(client, db_engine):
    _, keep_id, dup_id = _seed_two_near_identical(db_engine)
    email, password = make_admin(db_engine)
    admin_tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()

    groups = client.get("/api/v1/admin/vacancies/duplicates", headers=_auth(admin_tokens))
    assert groups.status_code == 200
    body = groups.json()
    assert len(body) == 1 and body[0]["keep"]["id"] == keep_id

    merge = client.post("/api/v1/admin/vacancies/merge", headers=_auth(admin_tokens),
                        json={"keep_id": keep_id, "duplicate_ids": [dup_id]})
    assert merge.status_code == 200 and merge.json()["merged"] == 1

    # Non-admin is refused both endpoints.
    _, tokens = register_and_login(client, email="not-admin@example.com")
    assert client.get("/api/v1/admin/vacancies/duplicates", headers=_auth(tokens)).status_code == 403
    assert client.post("/api/v1/admin/vacancies/merge", headers=_auth(tokens),
                       json={"keep_id": keep_id, "duplicate_ids": [dup_id]}).status_code == 403


def test_list_vacancies_flagged_filter(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    c = Company(company_name="Acme", careers_url="https://boards.greenhouse.io/acme")
    s.add(c); s.commit(); s.refresh(c)
    now = datetime.now(timezone.utc)
    clean = Vacancy(company_id=c.id, source_id="s1", title="Clean Role", content_hash="cl1",
                    is_open=True, first_seen_at=now, last_seen_at=now, trust_flags=[])
    flagged = Vacancy(company_id=c.id, source_id="s2", title="Flagged Role", content_hash="fl1",
                      is_open=True, first_seen_at=now, last_seen_at=now,
                      trust_flags=["payment_request"])
    s.add_all([clean, flagged]); s.commit()
    s.close()

    _, tokens = register_and_login(client)
    flagged_only = client.get("/api/v1/vacancies", params={"flagged": True}, headers=_auth(tokens)).json()
    assert {v["title"] for v in flagged_only} == {"Flagged Role"}
    clean_only = client.get("/api/v1/vacancies", params={"flagged": False}, headers=_auth(tokens)).json()
    assert {v["title"] for v in clean_only} == {"Clean Role"}
