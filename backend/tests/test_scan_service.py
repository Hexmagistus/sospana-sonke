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

    # Second scan: job 2 disappeared, job 1 unchanged -> no new rows, job 2 closed.
    second = [first[0]]
    with httpx.Client(transport=httpx.MockTransport(_greenhouse_handler(second))) as client:
        r2 = scan_source(db, src, client=client)
    assert r2.created == 0
    assert r2.updated == 1
    assert r2.closed == 1
    assert db.query(Vacancy).filter(Vacancy.company_id == c.id).count() == 2  # no duplicates
    closed = db.query(Vacancy).filter(Vacancy.title == "Data Analyst").first()
    assert closed.is_open is False


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


def test_scan_company_without_url(db):
    c = Company(company_name="NoURL", scraping_status="no_url")
    db.add(c); db.commit(); db.refresh(c)
    reports = scan_company(db, c)
    assert reports[0].status == "no_url"
