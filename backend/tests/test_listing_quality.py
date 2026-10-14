"""Listing quality: hide non-jobs, stale posts and dead links, then purge them."""
from datetime import datetime, timedelta, timezone

from app.models.admin_ops import AdminAuditLog
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.scheduler.registry import DEFAULT_SCHEDULE, JOBS
from app.services.listing_quality import (
    listing_quality_score,
    quality_failure_clause,
    removal_reasons_for,
    review_listing_quality,
    stamp_text_failures,
)
from app.services.opportunity_expiry import is_publicly_listed, sa_today
from app.services.opportunity_purge import purge_expired_opportunities


class _Response:
    def __init__(self, code: int, url: str):
        self.status_code = code
        self.url = url
        self.text = ""


class _Client:
    def __init__(self, codes: dict[str, int]):
        self.codes = codes
        self.closed = False

    def get(self, url):
        return _Response(self.codes.get(url, 200), url)

    def close(self):
        self.closed = True


def _add(db, source, title, **kwargs):
    now = datetime.now(timezone.utc)
    marker = kwargs.pop("content_hash", title)
    row = Vacancy(
        company_id=source.company_id,
        source_id=source.id,
        title=title,
        content_hash=f"h-{marker}",
        is_open=True,
        status="active",
        lifecycle_status="ACTIVE",
        first_seen_at=now,
        last_seen_at=now,
        opportunity_type="job",
        **kwargs,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _source(db):
    company = Company(
        company_name="Ward Hospital",
        country="South Africa",
        source_type="HOSPITAL",
        careers_url="https://ward.example/careers",
        active=True,
    )
    db.add(company)
    db.commit()
    source = VacancySource(company_id=company.id, url="https://ward.example/careers", ats_type="static", active=True)
    db.add(source)
    db.commit()
    return source


def test_quality_score_penalties():
    assert listing_quality_score([]) == 100
    assert listing_quality_score(["past_year"]) == 20
    assert listing_quality_score(["stale_posting"]) == 30
    assert listing_quality_score(["not_an_opportunity"]) == 0
    assert listing_quality_score(["dead_link"]) == 0
    assert listing_quality_score(["past_year", "stale_posting"]) == 0


def test_sql_and_python_agree_on_each_sample(db):
    today = sa_today()
    source = _source(db)
    samples = [
        ("Live Nurse", {"description": "Ward shift on the medical floor.", "closing_date": today + timedelta(days=3),
                        "posting_date": today - timedelta(days=2)}, []),
        ("News Casters", {"description": "Read the evening bulletin.", "closing_date": today + timedelta(days=5)}, []),
        ("Audit Article Trainee (CTA/ ACCA) 2027", {"description": "Training contract.", "closing_date": today + timedelta(days=10)}, []),
        ("Software Engineer, Privacy Engineering", {"description": "Build privacy controls.", "closing_date": today + timedelta(days=4)}, []),
        ("Vacancy: Senior Risk Officer Read More", {"description": "Apply on the employer site.", "closing_date": today + timedelta(days=6)}, []),
        ("VACANCY FOR THE POSITION OF GAMBLING COMMISSIONER", {
            "application_url": "https://www.gibraltar.gov.gi/press-releases/vacancy-for-the-position-of-gambling-commissioner-121",
            "closing_date": today + timedelta(days=8),
        }, []),
        ("Invitation to Learnership 2019", {"description": "Old intake.", "closing_date": today + timedelta(days=2)}, ["past_year"]),
        ("Nurse", {"description": "Closing date 23 September 2019.", "closing_date": today + timedelta(days=2)}, ["past_year"]),
        ("2024-2025 Learnership Programme", {"closing_date": today + timedelta(days=2)}, ["past_year"]),
        ("CANDIDATE LEGAL PRACTITIONER 2025", {"closing_date": today + timedelta(days=2)}, ["past_year"]),
        ("Nurse", {
            "content_hash": "stale",
            "posting_date": today - timedelta(days=121),
            "closing_date": None,
            "description": "Still listed, no closing date.",
        }, ["stale_posting"]),
        ("Nurse", {
            "content_hash": "old-but-open",
            "posting_date": today - timedelta(days=200),
            "closing_date": today + timedelta(days=2),
            "description": "A closing date keeps it.",
        }, []),
        ("Tsogo Sun Gaming Careers", {"description": "The company careers page.", "closing_date": today + timedelta(days=2)}, ["not_an_opportunity"]),
        ("Careers - Heirs Holdings", {"closing_date": today + timedelta(days=2)}, ["not_an_opportunity"]),
        ("NFVF Announces Appointment of New Chief Executive Officer", {"closing_date": today + timedelta(days=2)}, ["not_an_opportunity"]),
        ("SIU welcomes freezing of a pension fund", {"closing_date": today + timedelta(days=2)}, ["not_an_opportunity"]),
        ("NU researcher leads a study", {
            "application_url": "https://nu.edu.kz/news-en/nu-researchers-published-a-study/",
            "closing_date": today + timedelta(days=2),
        }, ["not_an_opportunity"]),
    ]
    for title, extra, expected in samples:
        row = _add(db, source, title, **extra)
        reasons = removal_reasons_for(row, today)
        sql_hit = db.query(Vacancy.id).filter(Vacancy.id == row.id, quality_failure_clause(today)).first() is not None
        assert reasons == expected, title
        assert sql_hit == bool(expected), title
        assert is_publicly_listed(row, today) == (not expected), title


def test_public_list_hides_bad_rows_and_purge_deletes_them(client, db):
    today = sa_today()
    source = _source(db)
    live = _add(
        db, source, "Live Nurse",
        description="Ward shift.",
        closing_date=today + timedelta(days=4),
        posting_date=today - timedelta(days=1),
        application_url="https://ward.example/jobs/live",
    )
    _add(db, source, "Learnership 2019", description="Closed years ago.", closing_date=today + timedelta(days=1))
    _add(
        db, source, "Old Nurse",
        content_hash="old-nurse",
        description="No closing date was stored.",
        posting_date=today - timedelta(days=200),
        closing_date=None,
    )
    _add(db, source, "International Careers", description="A landing page.")
    listed = client.get("/api/v1/jobs", params={"q": "Nurse"}).json()
    assert [job["title"] for job in listed["jobs"]] == ["Live Nurse"]
    deep = client.get("/api/v1/jobs", params={"offset": 550, "limit": 10})
    assert deep.status_code == 200
    assert deep.json()["matched"] >= 1
    too_far = client.get("/api/v1/jobs", params={"offset": 100001, "limit": 10})
    assert too_far.status_code == 422

    stamped = stamp_text_failures(db, today=today)
    assert stamped["past_year"] == 1
    assert stamped["stale_posting"] == 1
    assert stamped["not_an_opportunity"] == 1
    assert stamped["hidden"] == 3
    db.expire_all()
    assert db.get(Vacancy, live.id).status == "active"
    assert db.get(Vacancy, live.id).quality_score != 0

    purged = purge_expired_opportunities(db)
    assert purged["deleted"] == 3
    assert purged["backup"]
    assert db.get(Vacancy, live.id) is not None
    assert client.get("/api/v1/jobs", params={"q": "Nurse"}).json()["jobs"][0]["id"] == live.id
    gone = client.get("/api/v1/jobs", params={"q": "2019"})
    assert gone.status_code == 200
    assert gone.json()["jobs"] == []


def test_dead_link_is_hidden_and_a_live_link_stays(db):
    today = sa_today()
    source = _source(db)
    dead = _add(
        db, source, "Dead Link Nurse",
        application_url="https://ward.example/jobs/missing",
        closing_date=today + timedelta(days=3),
        description="The advert page is gone.",
    )
    live = _add(
        db, source, "Live Link Nurse",
        content_hash="live-link",
        application_url="https://ward.example/jobs/open",
        closing_date=today + timedelta(days=3),
        description="The advert page answers.",
    )
    shaky = _add(
        db, source, "Busy Link Nurse",
        content_hash="busy-link",
        application_url="https://ward.example/jobs/busy",
        closing_date=today + timedelta(days=3),
        description="The host had an error.",
    )
    client = _Client({
        dead.application_url: 404,
        live.application_url: 200,
        shaky.application_url: 500,
    })
    summary = review_listing_quality(db, client=client, link_limit=10, max_seconds=30, today=today, sleep=lambda _seconds: None)
    assert summary["dead_link"] == 1
    assert summary["links_checked"] == 3
    assert summary["hidden"] == 1
    db.expire_all()
    assert db.get(Vacancy, dead.id).status == "expired"
    assert db.get(Vacancy, dead.id).quality_score == 0
    assert db.get(Vacancy, dead.id).link_http_status == 404
    assert is_publicly_listed(db.get(Vacancy, live.id), today)
    assert is_publicly_listed(db.get(Vacancy, shaky.id), today)
    assert db.get(Vacancy, shaky.id).link_http_status == 500
    audit = db.query(AdminAuditLog).filter(AdminAuditLog.action == "review_listing_quality").one()
    assert "dead_link=1" in audit.detail
    assert "links_checked=3" in audit.detail
    second = review_listing_quality(db, client=client, link_limit=10, max_seconds=30, today=today, sleep=lambda _seconds: None)
    assert second["links_checked"] == 0


def test_quality_job_is_scheduled():
    assert "review_listing_quality" in JOBS
    assert DEFAULT_SCHEDULE["review_listing_quality"] == "15 1 * * *"
