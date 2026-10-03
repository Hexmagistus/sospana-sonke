"""Scan orchestration tests: create, dedup, change-detection, robots, requirements."""
import httpx

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancyRequirement
from app.services.scan_service import ensure_source, scan_source, scan_company


def _greenhouse_handler(jobs):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if "boards-api.greenhouse.io" in url:
            return httpx.Response(200, json={"jobs": jobs})
        return httpx.Response(404)
    return handler


def _mk_company(db):
    c = Company(company_name="Acme", jse_code="ACM",
                careers_url="https://boards.greenhouse.io/acme", scraping_status="pending")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_ensure_source_detects_ats(db):
    c = _mk_company(db)
    src = ensure_source(db, c)
    assert src is not None and src.ats_type == "greenhouse"
    assert src.config["token"] == "acme"
    # idempotent
    assert ensure_source(db, c).id == src.id


def test_scan_creates_vacancies_and_requirements(db):
    c = _mk_company(db)
    src = ensure_source(db, c)
    jobs = [
        {"id": 1, "title": "Operations Manager", "location": {"name": "Johannesburg"},
         "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
         "content": "<h3>Requirements</h3><ul><li>Must have 5 years experience</li>"
                    "<li>Degree required</li><li>SAP advantageous</li></ul>"},
        {"id": 2, "title": "Data Analyst", "location": {"name": "Remote"},
         "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
         "content": "<p>Join us</p>"},
    ]
    with httpx.Client(transport=httpx.MockTransport(_greenhouse_handler(jobs))) as client:
        report = scan_source(db, src, client=client)
    assert report.status == "ok"
    assert report.created == 2
    assert db.query(Vacancy).filter(Vacancy.company_id == c.id).count() == 2

    ops = db.query(Vacancy).filter(Vacancy.title == "Operations Manager").first()
    reqs = db.query(VacancyRequirement).filter(VacancyRequirement.vacancy_id == ops.id).all()
    kinds = {r.text: r.kind for r in reqs}
    assert any(k == "hard" for k in kinds.values())
    assert any("SAP" in t and kinds[t] == "soft" for t in kinds)


def test_rescan_dedupes_and_closes(db):
    c = _mk_company(db)
    src = ensure_source(db, c)
    first = [
        {"id": 1, "title": "Operations Manager", "location": {"name": "JHB"},
         "absolute_url": "u1", "content": "<p>role</p>"},
        {"id": 2, "title": "Data Analyst", "location": {"name": "CPT"},
         "absolute_url": "u2", "content": "<p>role</p>"},
    ]
    with httpx.Client(transport=httpx.MockTransport(_greenhouse_handler(first))) as client:
        r1 = scan_source(db, src, client=client)
    assert r1.created == 2

    # Second scan: job 2 disappeared. One miss is not enough to close it.
    second = [first[0]]
    with httpx.Client(transport=httpx.MockTransport(_greenhouse_handler(second))) as client:
        r2 = scan_source(db, src, client=client)
    assert r2.created == 0
    assert r2.updated == 1
    assert r2.closed == 0
    assert r2.duplicates_prevented == 1
    assert db.query(Vacancy).filter(Vacancy.company_id == c.id).count() == 2  # no duplicates
    missing = db.query(Vacancy).filter(Vacancy.title == "Data Analyst").first()
    assert missing.is_open is True
    assert missing.consecutive_misses == 1

    # Third successful scan still omitting job 2 closes it.
    with httpx.Client(transport=httpx.MockTransport(_greenhouse_handler(second))) as client:
        r3 = scan_source(db, src, client=client)
    assert r3.closed == 1
    db.refresh(missing)
    assert missing.is_open is False
    assert missing.lifecycle_status == "REMOVED"


def test_robots_disallowed_blocks_scan(db):
    c = _mk_company(db)
    src = ensure_source(db, c)

    def handler(request):
        if str(request.url).endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nDisallow: /")
        return httpx.Response(200, json={"jobs": [{"id": 1, "title": "X"}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = scan_source(db, src, client=client)
    assert report.status == "robots_disallowed"
    assert db.query(Vacancy).count() == 0
    assert src.robots_allowed is False


def test_http_error_records_failure(db):
    c = _mk_company(db)
    src = ensure_source(db, c)

    def handler(request):
        if str(request.url).endswith("robots.txt"):
            return httpx.Response(404)
        return httpx.Response(500, text="boom")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = scan_source(db, src, client=client, check_robots=True)
    assert report.status == "http_error"
    assert src.consecutive_failures == 1
    assert src.last_error


def test_bot_challenge_does_not_mark_the_source_broken(db):
    c = Company(company_name="PageUp Uni", careers_url="https://careers.example.edu/listing/",
                scraping_status="ok", active=True, country="Australia")
    db.add(c)
    db.commit()
    db.refresh(c)
    src = ensure_source(db, c)
    src.consecutive_failures = 0
    db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(
            202,
            text="<html>https://token.awswaf.com/challenge.js Human Verification</html>",
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = scan_source(db, src, client=client, check_robots=True)
    assert report.status == "blocked"
    assert src.last_status == "blocked"
    assert src.consecutive_failures == 0
    assert db.query(Vacancy).filter(Vacancy.company_id == c.id).count() == 0


def test_scan_company_without_url(db):
    c = Company(company_name="NoURL", scraping_status="no_url")
    db.add(c); db.commit(); db.refresh(c)
    reports = scan_company(db, c)
    assert reports[0].status == "no_url"


def test_wait_page_on_a_static_college_site_is_blocked_not_empty(db):
    """15 college sites answer HTTP 200 with a 'One moment, please...' reload page."""
    c = Company(company_name="Challenge College", careers_url="https://college.example.ac.za/vacancies/",
                scraping_status="ok", active=True, country="South Africa")
    db.add(c)
    db.commit()
    db.refresh(c)
    src = ensure_source(db, c)
    assert src.ats_type == "static"
    page = ("<html><head><title>One moment, please...</title></head><body>"
            "<script>setTimeout(function(){window.location.reload(true)},4000)</script></body></html>")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(200, text=page, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = scan_source(db, src, client=client, check_robots=True)
    assert report.status == "blocked"
    assert src.scraper_status == "BLOCKED" and src.last_success_at is None
    assert src.consecutive_failures == 0
    assert db.query(Vacancy).filter(Vacancy.company_id == c.id).count() == 0
