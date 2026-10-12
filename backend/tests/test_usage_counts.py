"""Anonymous daily totals: filters only, no question, no person, no address."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.migrations.usage_counts import downgrade, upgrade
from app.models.company import Company
from app.models.usage_count import UsageClickDaily, UsageSearchDaily
from app.models.vacancy import Vacancy
from app.services.intelligence_search import IntelligenceAnswer, Understood
from app.services.usage_counts import RETENTION_DAYS, classify_search, utc_today
from tests.conftest import make_admin, register_and_login


def _company(session, name, country, source_type, careers_url=None):
    company = Company(company_name=name, country=country, source_type=source_type, careers_url=careers_url)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def _role(session, company, title, application_url):
    now = datetime.now(timezone.utc)
    role = Vacancy(
        company_id=company.id,
        source_id="src-usage",
        title=title,
        content_hash=f"hash-{title}-{company.id}",
        is_open=True,
        first_seen_at=now,
        last_seen_at=now,
        application_url=application_url,
        location="Johannesburg",
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def _blob(db_engine) -> str:
    S = sessionmaker(bind=db_engine)
    session = S()
    try:
        parts: list[str] = []
        for model in (UsageSearchDaily, UsageClickDaily):
            columns = [column.name for column in model.__table__.columns]
            for row in session.query(model).all():
                parts.append("|".join("" if getattr(row, name) is None else str(getattr(row, name)) for name in columns))
        return "\n".join(sorted(parts))
    finally:
        session.close()


def test_classify_keeps_filters_and_drops_the_question():
    counted = classify_search(IntelligenceAnswer(
        question="Nursing for Ada Lovelace ada@example.com",
        understood=Understood(
            country="South Africa", looking_for="roles", supported=True, keywords="ada lovelace",
            source_types=("HOSPITAL",),
        ),
        vacancy_count=2,
        employer_count=1,
        vacancies=[
            {"application_url": "https://example.com/apply"},
            {"application_url": "javascript:alert(1)"},
        ],
        employers=[{"careers_url": "http://example.com/careers"}],
    ))
    assert counted.country == "South Africa"
    assert counted.category == "HOSPITAL"
    assert counted.intent == "roles"
    assert counted.outcome == "results"
    assert counted.result_bucket == "1-5"
    assert counted.results_returned == 3
    assert counted.results_with_source == 2
    assert "Ada" not in str(counted)
    assert "ada@example.com" not in str(counted)

    refused = classify_search(IntelligenceAnswer(
        question="What is the GDP of Ada Lovelace?",
        understood=Understood(supported=False, declined=("GDP",), looking_for="both"),
    ))
    assert refused.intent == "unsupported"
    assert refused.outcome == "not_enough_data"
    assert refused.result_bucket == "0"
    assert refused.results_returned == 0
    assert "GDP" not in str(refused)
    assert "Ada" not in str(refused)

    government = classify_search(IntelligenceAnswer(
        question="Government in South Africa",
        understood=Understood(
            supported=True, looking_for="employers", country="South Africa",
            source_types=("DEPT", "MUNI", "SOE", "Government", "Municipality", "Parastatal"),
        ),
        employer_count=4,
        employers=[{"careers_url": "not a link"}],
    ))
    assert government.category == "GOVERNMENT"
    assert government.result_bucket == "1-5"
    assert government.results_with_source == 0


def test_search_and_click_land_in_the_daily_totals(client, db_engine):
    S = sessionmaker(bind=db_engine)
    session = S()
    hospital = _company(session, "Groote Schuur", "South Africa", "HOSPITAL", "https://example.com/careers")
    role = _role(session, hospital, "Professional Nurse", "https://example.com/apply/nurse")
    _company(session, "Kenya Bureau", "Kenya", "DEPT")
    role_id = role.id
    hospital_id = hospital.id
    session.close()

    def search(question, headers=None):
        response = client.get("/api/v1/intelligence/search", params={"q": question}, headers=headers or {})
        assert response.status_code == 200, response.text
        return response.json()

    first = search("Nursing jobs in South Africa", {"X-Forwarded-For": "203.0.113.50"})
    assert first["vacancy_count"] >= 1
    assert "Ada" not in first["question"]
    search("Nursing jobs in South Africa")
    search("Nursing jobs in Kenya")
    search("What is the GDP?")
    search("Hospitals in South Africa")
    before = _blob(db_engine)
    search("Nursing jobs in South Africa", {"DNT": "1"})
    search("What is the GDP?", {"Sec-GPC": "1"})
    search("Hospitals in South Africa", {"X-Privacy-Opt-Out": "1"})
    assert _blob(db_engine) == before

    clicked = client.post("/api/v1/intelligence/clicks", json={
        "target": "vacancy",
        "id": role_id,
        "email": "ada@example.com",
        "question": "Ada Lovelace",
        "ip": "203.0.113.50",
    })
    assert clicked.status_code == 204, clicked.text
    again = client.post("/api/v1/intelligence/clicks", json={"target": "vacancy", "id": role_id}, headers={"DNT": "1"})
    assert again.status_code == 204
    employer = client.post("/api/v1/intelligence/clicks", json={"target": "employer", "id": hospital_id})
    assert employer.status_code == 204

    stored = _blob(db_engine)
    for secret in ("Ada Lovelace", "ada@example.com", "203.0.113.50", "GDP", "Professional Nurse", "Groote Schuur"):
        assert secret not in stored
    search_columns = {column["name"] for column in inspect(db_engine).get_columns("usage_search_daily")}
    click_columns = {column["name"] for column in inspect(db_engine).get_columns("usage_click_daily")}
    assert "user_id" not in search_columns
    assert "ip" not in click_columns
    assert "question" not in search_columns
    assert search_columns == {
        "id", "day", "country", "category", "intent", "outcome", "result_bucket",
        "searches", "results_returned", "results_with_source",
    }

    check = S()
    try:
        nurse = check.query(UsageSearchDaily).filter(
            UsageSearchDaily.country == "South Africa",
            UsageSearchDaily.intent == "roles",
            UsageSearchDaily.outcome == "results",
        ).one()
        assert nurse.searches == 2
        assert nurse.category == ""
        assert nurse.result_bucket == "1-5"
        assert check.query(UsageSearchDaily).filter(UsageSearchDaily.outcome == "not_enough_data").one().intent == "unsupported"
        assert check.query(UsageSearchDaily).filter(UsageSearchDaily.category == "HOSPITAL").one().intent == "employers"
        assert check.query(UsageClickDaily).filter(UsageClickDaily.target_id == role_id).one().clicks == 1
        assert check.query(UsageClickDaily).filter(UsageClickDaily.target_id == hospital_id).one().clicks == 1
    finally:
        check.close()

    empty = client.get("/api/v1/intelligence/admin/scorecard")
    assert empty.status_code == 401
    _, tokens = register_and_login(client, email="reader-usage@example.com")
    refused = client.get(
        "/api/v1/intelligence/admin/scorecard",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert refused.status_code == 403

    admin_email, admin_password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password}).json()
    card = client.get(
        "/api/v1/intelligence/admin/scorecard",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert card.status_code == 200, card.text
    body = card.json()
    assert body["searches"] == 5
    assert body["searches_with_results"] == 3
    assert body["searches_empty"] == 1
    assert body["searches_not_enough_data"] == 1
    assert body["search_success_rate"] == 0.6
    assert body["not_enough_data_rate"] == 0.2
    assert body["clicks"] == 2
    assert body["click_through_rate"] == round(2 / 3, 4)
    assert body["results_returned"] == 6
    assert body["results_with_source"] == 6
    assert body["source_link_rate"] == 1.0
    assert body["retention_days"] == 90
    assert "question" not in body
    assert "ada@example.com" not in card.text
    labels = {row["label"] for row in body["clicks_by_target"]}
    assert "Professional Nurse" in labels
    assert "Groote Schuur" in labels


def test_click_rejects_unknown_and_deleted_rows(client, db_engine):
    S = sessionmaker(bind=db_engine)
    session = S()
    company = _company(session, "Closed Hospital", "South Africa", "HOSPITAL", "https://example.com/careers")
    role = _role(session, company, "Closed Role", "https://example.com/apply")
    role.deleted_at = datetime.now(timezone.utc)
    session.commit()
    role_id = role.id
    session.close()

    missing = client.post("/api/v1/intelligence/clicks", json={
        "target": "vacancy", "id": "00000000-0000-4000-8000-000000000000",
    })
    assert missing.status_code == 422
    bad = client.post("/api/v1/intelligence/clicks", json={"target": "person", "id": role_id})
    assert bad.status_code == 422
    deleted = client.post("/api/v1/intelligence/clicks", json={"target": "vacancy", "id": role_id})
    assert deleted.status_code == 422
    assert _blob(db_engine) == ""


def test_retention_drops_totals_older_than_the_window(client, db_engine):
    S = sessionmaker(bind=db_engine)
    session = S()
    _company(session, "Retention Hospital", "South Africa", "HOSPITAL", "https://example.com/careers")
    today = utc_today()
    session.add(UsageSearchDaily(
        day=today - timedelta(days=RETENTION_DAYS),
        country="South Africa", category="", intent="roles", outcome="results",
        result_bucket="1-5", searches=9, results_returned=9, results_with_source=9,
    ))
    session.add(UsageSearchDaily(
        day=today - timedelta(days=RETENTION_DAYS - 1),
        country="Kenya", category="", intent="roles", outcome="empty",
        result_bucket="0", searches=4, results_returned=0, results_with_source=0,
    ))
    session.commit()
    session.close()

    response = client.get("/api/v1/intelligence/search", params={"q": "What is the GDP?"})
    assert response.status_code == 200
    check = S()
    try:
        days = {row.day for row in check.query(UsageSearchDaily).all()}
        assert today - timedelta(days=RETENTION_DAYS) not in days
        assert today - timedelta(days=RETENTION_DAYS - 1) in days
        assert today in days
    finally:
        check.close()


def test_usage_migration_upgrades_and_rolls_back():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    upgrade(engine)
    upgrade(engine)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO usage_search_daily "
            "(id, day, country, category, intent, outcome, result_bucket, searches, results_returned, results_with_source) "
            "VALUES ('s1', '2026-10-12', 'South Africa', 'HOSPITAL', 'roles', 'results', '1-5', 1, 1, 1)"
        ))
        conn.execute(text(
            "INSERT INTO usage_click_daily (id, day, target_kind, target_id, clicks) "
            "VALUES ('c1', '2026-10-12', 'vacancy', '00000000-0000-4000-8000-000000000001', 2)"
        ))
        assert conn.execute(text("SELECT searches FROM usage_search_daily")).scalar() == 1
    downgrade(engine)
    names = set(inspect(engine).get_table_names())
    assert "usage_search_daily" not in names
    assert "usage_click_daily" not in names
    upgrade(engine)
    with engine.begin() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM usage_search_daily")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM usage_click_daily")).scalar() == 0
    engine.dispose()
