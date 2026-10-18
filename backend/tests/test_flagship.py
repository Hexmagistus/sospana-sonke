"""South Africa leads public lists unless the caller names a country."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.models.vacancy import Vacancy
from app.services.flagship import FLAGSHIP_COUNTRY, countries_flagship_first
from app.services.intelligence_search import answer_question


# Relative to the real clock: public lists hide roles not seen for 7 days and
# roles whose closing day has passed, so a fixed date here expires the test.
NOW = datetime.now(timezone.utc) - timedelta(minutes=5)
TODAY = date.today()


def _role(session, name, country, title, *, seen, closing=None, role_country=None):
    company = Company(company_name=name, country=country, source_type="PRIVATE", active=True)
    session.add(company)
    session.commit()
    row = Vacancy(
        company_id=company.id,
        source_id="src",
        title=title,
        content_hash=title,
        is_open=True,
        first_seen_at=seen,
        last_seen_at=seen,
        closing_date=closing,
        country=role_country,
    )
    session.add(row)
    session.commit()
    return row


def test_flagship_name_sorts_south_africa_first():
    assert FLAGSHIP_COUNTRY == "South Africa"
    assert countries_flagship_first(["Kenya", "South Africa", "Botswana"]) == [
        "South Africa", "Botswana", "Kenya",
    ]


def test_public_jobs_list_south_africa_before_a_newer_foreign_role(client, db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        _role(s, "Nairobi Works", "Kenya", "Newer Nurse", seen=NOW)
        _role(s, "Cape Works", "South Africa", "Older Nurse", seen=NOW - timedelta(days=3))
        _role(
            s, "Mixed Works", "Kenya", "Posted In SA",
            seen=NOW - timedelta(days=1), role_country="South Africa",
        )
    finally:
        s.close()

    listed = client.get("/api/v1/jobs")
    assert listed.status_code == 200, listed.text
    titles = [row["title"] for row in listed.json()["jobs"]]
    assert titles.index("Older Nurse") < titles.index("Newer Nurse")
    assert titles.index("Posted In SA") < titles.index("Newer Nurse")

    kenya = client.get("/api/v1/jobs", params={"country": "Kenya"}).json()
    assert [row["title"] for row in kenya["jobs"]] == ["Newer Nurse", "Posted In SA"]

    facets = client.get("/api/v1/jobs/facets").json()
    names = [row["name"] for row in facets["countries"]]
    assert names[0] == "South Africa"


def test_closing_sort_still_puts_south_africa_first(client, db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        _role(
            s, "Nairobi Works", "Kenya", "Soon Abroad",
            seen=NOW, closing=TODAY + timedelta(days=7),
        )
        _role(
            s, "Cape Works", "South Africa", "Later At Home",
            seen=NOW - timedelta(days=2), closing=TODAY + timedelta(days=19),
        )
    finally:
        s.close()

    dated = client.get("/api/v1/jobs", params={"sort": "closing"}).json()
    titles = [row["title"] for row in dated["jobs"]]
    assert titles.index("Later At Home") < titles.index("Soon Abroad")


def test_search_without_a_country_lists_south_africa_first(client, db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        _role(s, "Nairobi Works", "Kenya", "Nurse", seen=NOW)
        _role(s, "Cape Works", "South Africa", "Nurse", seen=NOW - timedelta(days=4))
        s.commit()
    finally:
        s.close()

    s = S()
    try:
        answer = answer_question(s, "nursing jobs")
    finally:
        s.close()
    assert answer.understood.country is None
    assert "South Africa is listed first" in answer.reading
    assert [row["company_country"] for row in answer.vacancies][0] == "South Africa"
