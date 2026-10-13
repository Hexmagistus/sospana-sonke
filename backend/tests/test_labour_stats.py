"""The stored Stats SA table, and the questions it is allowed to answer."""
from app.models.usage_count import UsageSearchDaily
from app.services.labour_stats import load_table, public_document


def test_table_matches_the_published_release():
    table = load_table()
    assert table is not None
    assert table["publisher"] == "Statistics South Africa"
    assert table["release_date"] == "2026-08-11"
    assert table["release_url"].endswith("/P02112ndQuarter2026.pdf")
    assert "Table E" in table["table"]
    assert "acknowledged as the original source" in table["licence"]
    assert "offered for sale" in table["licence"]
    assert table["download_permitted"] is False
    assert [row["place"] for row in table["rows"]][0] == "South Africa"
    limpopo = next(row for row in table["rows"] if row["place"] == "Limpopo")
    assert limpopo["official"] == ["35,0", "31,7", "32,0"]
    assert limpopo["expanded"] == ["47,7", "47,0", "46,7"]
    national = table["rows"][0]
    assert national["official"][-1] == "33,6"
    assert national["expanded"][-1] == "43,8"
    document = public_document()
    assert document["loaded"] is True
    assert "33,6" in str(document["rows"][0]["official"])


def test_limpopo_question_cites_the_table_and_stores_no_question(client, db_engine):
    listed = client.get("/api/v1/labour/south-africa")
    assert listed.status_code == 200
    assert listed.json()["loaded"] is True
    assert listed.json()["download_permitted"] is False

    response = client.get("/api/v1/intelligence/search", params={"q": "unemployment in Limpopo"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["enough_data"] is True
    assert body["llm"] == "disabled"
    assert body["vacancies"] == []
    assert body["employers"] == []
    assert "32,0%" in body["summary"]
    assert "31,7%" in body["summary"]
    assert "35,0%" in body["summary"]
    assert "Statistics South Africa" in body["summary"]
    assert "2026-08-11" in body["summary"]
    assert body["citation"]["place"] == "Limpopo"
    assert body["citation"]["series"] == "official"
    assert body["citation"]["url"].startswith("https://www.statssa.gov.za/")
    assert "caused" not in body["summary"].lower()
    emailed = client.get(
        "/api/v1/intelligence/search",
        params={"q": "unemployment in Limpopo, email me at person@example.com"},
    )
    assert "person@example.com" not in emailed.json()["summary"]
    assert "person@example.com" not in str(emailed.json().get("citation"))
    assert any("did not re-estimate" in line for line in body["limitations"])
    assert any("not an explanation" in line for line in body["limitations"])

    from sqlalchemy.orm import sessionmaker
    check = sessionmaker(bind=db_engine)()
    try:
        rows = check.query(UsageSearchDaily).all()
        statistic = [row for row in rows if row.intent == "statistic"]
        stored = " ".join(
            f"{row.country}|{row.category}|{row.intent}|{row.outcome}|{row.result_bucket}"
            for row in rows
        )
    finally:
        check.close()
    assert len(statistic) == 1
    assert statistic[0].country == "South Africa"
    assert statistic[0].outcome == "results"
    assert statistic[0].result_bucket == "1-5"
    assert "person@" not in stored
    assert "Limpopo" not in stored
    assert "unemployment" not in stored.lower()


def test_other_questions_do_not_invent_a_rate(client):
    gdp = client.get("/api/v1/intelligence/search", params={"q": "What is the GDP?"})
    assert gdp.status_code == 200
    assert gdp.json()["enough_data"] is False
    assert gdp.json()["citation"] is None
    assert "33,6" not in gdp.text

    kenya = client.get("/api/v1/intelligence/search", params={"q": "unemployment in Kenya"})
    assert kenya.json()["enough_data"] is False
    assert "33,6" not in kenya.text
    assert "32,0" not in kenya.text
    assert "did not guess" in kenya.json()["summary"]

    city = client.get("/api/v1/intelligence/search", params={"q": "unemployment in Cape Town"})
    assert city.json()["enough_data"] is False
    assert "19,5" not in city.text
    assert "did not substitute" in city.json()["summary"]

    youth = client.get("/api/v1/intelligence/search", params={"q": "youth unemployment in Limpopo"})
    assert youth.json()["enough_data"] is False
    assert "32,0%" not in youth.json()["summary"]

    expanded = client.get("/api/v1/intelligence/search", params={"q": "expanded unemployment in Limpopo"})
    assert expanded.json()["enough_data"] is True
    assert "46,7%" in expanded.json()["summary"]
    assert expanded.json()["citation"]["series"] == "expanded"


def test_a_job_question_does_not_mix_in_the_rate(client, db_engine):
    from datetime import datetime, timezone
    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company
    from app.models.vacancy import Vacancy

    session = sessionmaker(bind=db_engine)()
    try:
        company = Company(company_name="Ward Hospital", country="South Africa", source_type="HOSPITAL", careers_url="https://ward.example/careers")
        session.add(company)
        session.commit()
        now = datetime.now(timezone.utc)
        session.add(Vacancy(
            company_id=company.id, source_id="src", title="Professional Nurse",
            content_hash="nurse-labour", is_open=True, first_seen_at=now, last_seen_at=now,
            description="secret advert",
        ))
        session.commit()
    finally:
        session.close()

    mixed = client.get("/api/v1/intelligence/search", params={"q": "Nursing jobs in South Africa and the unemployment rate"})
    body = mixed.json()
    assert body["enough_data"] is True
    assert body["vacancy_count"] == 1
    assert body["citation"] is None
    assert "33,6" not in mixed.text
    assert "not mixed into this job count" in body["summary"]
    assert "secret advert" not in mixed.text
