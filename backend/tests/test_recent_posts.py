"""GET /jobs?sort=recent: newest open roles first, SA-first only as a tiebreak."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.models.vacancy import Vacancy
from app.services.recent_posts import sort_recent

NOW = datetime.now(timezone.utc) - timedelta(minutes=5)
TODAY = date.today()


def _role(session, name, country, title, *, seen, posted=None, closing=None, is_open=True):
    company = Company(company_name=name, country=country, source_type="PRIVATE", active=True)
    session.add(company)
    session.commit()
    session.add(Vacancy(
        company_id=company.id, source_id="src", title=title, content_hash=title,
        is_open=is_open, first_seen_at=seen, last_seen_at=seen,
        posting_date=posted, closing_date=closing,
    ))
    session.commit()


def _titles(client, **params):
    r = client.get("/api/v1/jobs", params={"sort": "recent", **params})
    assert r.status_code == 200, r.text
    return [row["title"] for row in r.json()["jobs"]]


def test_recent_is_strictly_newest_first_even_over_south_africa(client, db_engine):
    s = sessionmaker(bind=db_engine)()
    try:
        _role(s, "Cape Works", "South Africa", "SA two days", seen=NOW - timedelta(days=2))
        _role(s, "Nairobi Works", "Kenya", "Kenya today", seen=NOW)
        _role(s, "Gabs Works", "Botswana", "Botswana yesterday", seen=NOW - timedelta(days=1))
    finally:
        s.close()
    assert _titles(client) == ["Kenya today", "Botswana yesterday", "SA two days"]
    # The default list still puts South Africa first.
    default = [r["title"] for r in client.get("/api/v1/jobs").json()["jobs"]]
    assert default[0] == "SA two days"


def test_stated_posting_date_beats_scan_day(client, db_engine):
    s = sessionmaker(bind=db_engine)()
    try:
        # Found today, but the advert says it was posted five days ago.
        _role(s, "Old Ad", "South Africa", "Posted five days ago", seen=NOW, posted=TODAY - timedelta(days=5))
        _role(s, "New Ad", "South Africa", "Found yesterday", seen=NOW - timedelta(days=1))
    finally:
        s.close()
    assert _titles(client, limit=10) == ["Found yesterday", "Posted five days ago"]


def test_same_day_ties_follow_country_bands(client, db_engine):
    s = sessionmaker(bind=db_engine)()
    try:
        day = TODAY - timedelta(days=1)
        _role(s, "UK Co", "United Kingdom", "UK", seen=NOW, posted=day)
        _role(s, "Ke Co", "Kenya", "Kenya", seen=NOW, posted=day)
        _role(s, "Zm Co", "Zambia", "Zambia", seen=NOW, posted=day)
        _role(s, "Za Co", "South Africa", "SA", seen=NOW, posted=day)
    finally:
        s.close()
    assert _titles(client) == ["SA", "Zambia", "Kenya", "UK"]


def test_recent_excludes_closed_and_past_closing(client, db_engine):
    s = sessionmaker(bind=db_engine)()
    try:
        _role(s, "A", "South Africa", "Open", seen=NOW)
        _role(s, "B", "South Africa", "Closed flag", seen=NOW, is_open=False)
        _role(s, "C", "South Africa", "Closing passed", seen=NOW, closing=TODAY - timedelta(days=1))
        _role(s, "D", "South Africa", "Closes today", seen=NOW, closing=TODAY)
    finally:
        s.close()
    assert sorted(_titles(client)) == ["Closes today", "Open"]


def test_newest_is_an_alias(client, db_engine):
    s = sessionmaker(bind=db_engine)()
    try:
        _role(s, "A", "South Africa", "Older", seen=NOW - timedelta(days=1))
        _role(s, "B", "Kenya", "Newer", seen=NOW)
    finally:
        s.close()
    r = client.get("/api/v1/jobs", params={"sort": "newest"})
    assert [x["title"] for x in r.json()["jobs"]] == ["Newer", "Older"]


def test_snapshot_twin_orders_the_same_way():
    jobs = [
        {"id": "1", "title": "uk", "company_country": "United Kingdom", "posting_date": "2026-11-20", "first_seen_at": "2026-11-21T10:00:00Z"},
        {"id": "2", "title": "sa", "company_country": "South Africa", "posting_date": "2026-11-20", "first_seen_at": "2026-11-21T10:00:00Z"},
        {"id": "3", "title": "new", "company_country": "Kenya", "posting_date": None, "first_seen_at": "2026-11-22T08:00:00Z"},
        {"id": "4", "title": "old", "company_country": "South Africa", "posting_date": "2026-10-01", "first_seen_at": "2026-11-22T09:00:00Z"},
    ]
    assert [j["title"] for j in sort_recent(jobs)] == ["new", "sa", "uk", "old"]
