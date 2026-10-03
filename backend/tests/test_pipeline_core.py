"""Core pipeline: canonical URLs, SSRF, sanitising, fingerprint, lifecycle, quality.

These tests use fixture HTML and a mock HTTP transport. They do not call live sites.
"""
import httpx

from app.models.company import Company
from app.models.scan_log import ScanLog
from app.models.vacancy import Vacancy
from app.scraper.base import RawVacancy, html_to_text
from app.scraper.fingerprint import vacancy_fingerprint
from app.scraper.normalise import prepare_listing
from app.scraper.ssrf import SsrfBlocked, assert_safe_fetch_url, classify_url
from app.scraper.urls import canonical_listing_url, safe_application_url
from app.services.scan_service import ensure_source, scan_source


def test_canonical_listing_strips_tracking_but_application_url_keeps_query():
    listing = canonical_listing_url(
        "https://Jobs.Example.com/roles/12/?utm_source=newsletter&id=12#apply"
    )
    assert listing == "https://jobs.example.com/roles/12?id=12"
    application = safe_application_url(
        "https://jobs.example.com/apply?job=12&utm_source=x#step"
    )
    assert application == "https://jobs.example.com/apply?job=12&utm_source=x#step"
    assert safe_application_url("javascript:alert(1)") is None


def test_ssrf_blocks_literal_private_and_resolved_loopback():
    assert classify_url("http://127.0.0.1/admin") == "private_ip"
    assert classify_url("http://169.254.169.254/latest/meta-data") == "private_ip"
    assert classify_url("http://localhost/secret") == "blocked_host"
    assert classify_url("file:///etc/passwd") == "bad_scheme"
    assert classify_url("https://careers.example.com/jobs", resolve=lambda host: ["8.8.8.8"]) == "ok"
    assert classify_url("https://careers.example.com/jobs", resolve=lambda host: ["127.0.0.1"]) == "dns_private"
    try:
        assert_safe_fetch_url("https://careers.example.com/jobs", resolve=lambda host: ["10.1.1.1"])
    except SsrfBlocked as exc:
        assert exc.verdict == "dns_private"
    else:
        raise AssertionError("private DNS result was fetched")


def test_html_to_text_drops_script_contents():
    text = html_to_text(
        "<p>Nurse</p><script>alert('xss')</script><li>Degree required</li>"
        "<a href=\"javascript:alert(1)\">Apply</a>"
    )
    assert "Nurse" in text
    assert "alert" not in text
    assert "Degree required" in text


def test_fingerprint_ignores_description_changes():
    first = vacancy_fingerprint("co", "99", "Nurse", "Gaborone")
    second = vacancy_fingerprint("co", "99", "Nurse (updated wording)", "Gaborone")
    assert first == second
    untitled = vacancy_fingerprint("co", None, "Nurse", "Gaborone")
    moved = vacancy_fingerprint("co", None, "Nurse", "Francistown")
    assert untitled != moved


def test_prepare_listing_leaves_unknowns_blank_and_scores_completeness():
    raw = RawVacancy(
        title="Ward Clerk",
        external_id="A-1",
        location="Gaborone",
        salary="Market related",
        application_url="https://jobs.example.com/apply?id=A-1",
        description="Join the team.",
    )
    fields = prepare_listing(
        raw, company_id="co", company_name="Clinic", company_country="Botswana",
        source_url="https://jobs.example.com/careers",
    )
    assert fields["country"] == "Botswana"
    assert fields["province"] is None
    assert fields["city"] is None
    assert fields["salary_min"] is None
    assert fields["salary_currency"] is None
    assert fields["verification_state"] == "DISCOVERED"
    assert fields["lifecycle_status"] == "ACTIVE"
    assert fields["application_url"].endswith("id=A-1")
    assert 0 < fields["quality_score"] < 100

    closed = RawVacancy(title="Driver", description="This position has been filled.")
    closed_fields = prepare_listing(
        closed, company_id="co", company_name="Clinic", company_country=None, source_url=None,
    )
    assert closed_fields["lifecycle_status"] == "CLOSED"
    assert closed_fields["is_open"] is False


def test_scan_writes_a_log_and_does_not_duplicate_when_the_wording_changes(db):
    company = Company(
        company_name="Clinic", country="Botswana",
        careers_url="https://boards.greenhouse.io/clinic", scraping_status="pending",
    )
    db.add(company)
    db.commit()
    source = ensure_source(db, company)
    jobs = [{
        "id": 7, "title": "Ward Clerk", "location": {"name": "Gaborone"},
        "absolute_url": "https://boards.greenhouse.io/clinic/jobs/7?utm_source=board",
        "content": "<p>Join us</p>",
    }]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if "boards-api.greenhouse.io" in url:
            return httpx.Response(200, json={"jobs": jobs})
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first = scan_source(db, source, client=client)
    assert first.created == 1
    row = db.query(Vacancy).filter(Vacancy.company_id == company.id).one()
    assert row.country == "Botswana"
    assert row.verification_state == "DISCOVERED"
    assert row.lifecycle_status == "ACTIVE"
    assert row.canonical_url == "https://boards.greenhouse.io/clinic/jobs/7"
    assert "utm_source" not in (row.canonical_url or "")
    assert row.application_url == "https://boards.greenhouse.io/clinic/jobs/7?utm_source=board"
    assert db.query(ScanLog).filter(ScanLog.company_id == company.id).count() == 1

    jobs[0]["content"] = "<p>Join us. Updated copy that must not create a second row.</p>"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        second = scan_source(db, source, client=client)
    assert second.created == 0
    assert second.duplicates_prevented == 1
    assert db.query(Vacancy).filter(Vacancy.company_id == company.id).count() == 1
    assert source.scraper_status == "SUCCESS"


def test_private_careers_url_is_refused(db):
    company = Company(
        company_name="Loop", careers_url="http://127.0.0.1/jobs", scraping_status="pending",
    )
    db.add(company)
    db.commit()
    source = ensure_source(db, company)

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"private URL was fetched: {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = scan_source(db, source, client=client, check_robots=False)
    assert report.status == "invalid_url"
    assert source.scraper_status == "INVALID_URL"
    assert db.query(Vacancy).count() == 0


def test_javascript_board_is_not_treated_as_an_empty_careers_page(db):
    company = Company(
        company_name="SF", careers_url="https://career5.successfactors.eu/careers",
        scraping_status="ok", country="Kenya",
    )
    db.add(company)
    db.commit()
    source = ensure_source(db, company)
    source.last_vacancy_count = 4
    db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        raise AssertionError("a browser-only board was fetched")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = scan_source(db, source, client=client)
    assert report.status == "javascript_required"
    assert source.scraper_status == "JAVASCRIPT_REQUIRED"
    assert source.consecutive_failures == 0
    assert source.last_status != "empty"
