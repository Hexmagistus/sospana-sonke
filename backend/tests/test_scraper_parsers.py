"""Parser tests against saved sample payloads (offline, via httpx.MockTransport)."""
import json
from pathlib import Path

import httpx

from datetime import date

from app.scraper.base import detect_ats, get_strategy, html_to_text
from app.scraper.breezy import BreezyStrategy
from app.scraper.cihr import CihrStrategy
from app.scraper.extract import normalize_date
from app.scraper.greenhouse import GREENHOUSE_DETAIL_LIMIT, GreenhouseStrategy
from app.scraper.politeness import MAX_RESPONSE_BYTES
from app.scraper.lever import LeverStrategy
from app.scraper.oracle_ce import OracleCEStrategy
from app.scraper.pinpoint import PinpointStrategy
from app.scraper.recruitee import RecruiteeStrategy
from app.scraper.smartrecruiters import SmartRecruitersStrategy
from app.scraper.workable import WorkableStrategy
from app.scraper.workday import WorkdayStrategy
from app.scraper.static_html import StaticHTMLStrategy

_FIXTURES = Path(__file__).parent / "fixtures" / "scraper"


def _fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


class _Src:
    def __init__(self, url, ats_type, config):
        self.url, self.ats_type, self.config = url, ats_type, config


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_detect_ats():
    assert detect_ats("https://boards.greenhouse.io/acme")[0] == "greenhouse"
    assert detect_ats("https://boards.greenhouse.io/acme")[1]["token"] == "acme"
    assert detect_ats("https://jobs.lever.co/acme")[0] == "lever"
    assert detect_ats("https://careers.smartrecruiters.com/AcmeCo")[0] == "smartrecruiters"
    assert detect_ats("https://jobs.smartrecruiters.com/bluescope")[1]["token"] == "bluescope"
    assert detect_ats("https://acme.smartrecruiters.com/careers")[1]["token"] == "acme"
    assert detect_ats("https://acme.recruitee.com/careers")[0] == "recruitee"
    assert detect_ats("https://acme.recruitee.com/careers")[1]["token"] == "acme"
    assert detect_ats("https://apply.workable.com/acme-inc/")[0] == "workable"
    assert detect_ats("https://apply.workable.com/acme-inc/")[1]["token"] == "acme-inc"
    assert detect_ats("https://www.goldfields.com/careers/")[0] == "static"
    assert detect_ats("https://job-boards.greenhouse.io/takealotcom")[1]["token"] == "takealotcom"
    eu = detect_ats("https://jobs.eu.lever.co/prosus")
    assert eu[0] == "lever" and eu[1]["api_base"] == "https://api.eu.lever.co"
    assert detect_ats("https://careers.unilever.com/en/south-africa")[0] == "static"
    assert detect_ats("https://www.unilever.com.gh/careers")[0] == "static"
    wd = detect_ats("https://absa.wd3.myworkdayjobs.com/ABSAcareersite")
    assert wd[0] == "workday" and wd[1]["tenant"] == "absa" and wd[1]["site"] == "ABSAcareersite"
    site = detect_ats("https://wd1.myworkdaysite.com/recruiting/abinbev/SAB")
    assert site[0] == "workday" and site[1]["tenant"] == "abinbev" and site[1]["site"] == "SAB"
    ora = detect_ats("https://fa-etyi-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/MrPriceGroupCareers/jobs")
    assert ora[0] == "oracle" and ora[1]["site_number"] == "CX" and ora[1]["site_name"] == "MrPriceGroupCareers"
    cx = detect_ats("https://iaccgs.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs")
    assert cx[1]["site_number"] == "CX_1"
    assert detect_ats("https://isuzu.breezy.hr/")[0] == "breezy"
    assert detect_ats("https://kempinski.pinpointhq.com/postings")[0] == "pinpoint"
    assert detect_ats("https://career5.successfactors.eu/careers")[0] == "js"
    assert detect_ats("https://atns.ci.hr/applicant/index.php?controller=Page&name=jobsearch")[0] == "cihr"
    assert detect_ats("https://astral.ci.hr/index.php?controller=Page&name=jobsearch")[1]["host"] == "astral.ci.hr"
    assert detect_ats("https://nefcareers.ci.hr/?controller=Page&name=jobsearch")[0] == "cihr"
    assert detect_ats("https://assmang.ci.hr")[0] == "cihr"
    assert detect_ats("https://careers.unilever.com/ci.hr")[0] == "static"
    assert get_strategy("cihr").ats_type == "cihr"
    assert detect_ats("https://careers.discovery.co.za/go/All-Jobs/4509301")[0] == "icims"
    assert detect_ats("https://careers.mediclinic.com/SouthernAfrica/go/Search-By-Keyword-MCSA/5071601/")[0] == "icims"
    assert detect_ats("https://jobs.aeciworld.com/search/?createNewAlert=false&q=")[0] == "icims"
    assert detect_ats("https://careers-acme.icims.com/jobs/intro")[0] == "icims"
    # A /go/ path without the portal id, and a government e-recruitment site, stay static.
    assert detect_ats("https://example.com/go/home")[0] == "static"
    assert detect_ats("https://erecruitment.saps.gov.za/SAPS-Vacancies/")[0] == "static"
    assert get_strategy("icims").ats_type == "icims"


def test_html_to_text_preserves_bullets():
    html = "<h3>Requirements</h3><ul><li>Must have 5 years</li><li>Degree required</li></ul>"
    text = html_to_text(html)
    lines = text.splitlines()
    assert "Requirements" in lines[0]
    assert any("Must have 5 years" in ln for ln in lines)
    assert any("Degree required" in ln for ln in lines)


def test_greenhouse_parser():
    def handler(request):
        assert "boards-api.greenhouse.io" in str(request.url)
        return httpx.Response(200, json={"jobs": [
            {"id": 101, "title": "Operations Manager",
             "location": {"name": "Johannesburg"},
             "departments": [{"name": "Operations"}],
             "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
             "updated_at": "2026-08-01T10:00:00Z",
             "content": "<h3>Requirements</h3><ul><li>Must have 5 years experience</li></ul>"},
        ]})
    src = _Src("https://boards.greenhouse.io/acme", "greenhouse", {"token": "acme"})
    with _client(handler) as c:
        vacs = GreenhouseStrategy().fetch(src, c)
    assert len(vacs) == 1
    assert vacs[0].title == "Operations Manager"
    assert vacs[0].external_id == "101"
    assert vacs[0].location == "Johannesburg"
    assert "Must have 5 years experience" in vacs[0].description


def test_greenhouse_large_board_keeps_the_list_when_content_exceeds_the_cap():
    """Anthropic's content=true body is ~9 MB. The list feed is the count."""
    assert MAX_RESPONSE_BYTES == 5_000_000
    assert GREENHOUSE_DETAIL_LIMIT == 40
    payload = json.loads(_fixture("greenhouse_light_list.json"))
    seen: list[str] = []

    def handler(request):
        url = str(request.url)
        seen.append(url)
        assert "content=true" not in url.split("?", 1)[0]
        if "content=true" in url:
            # Real politeness cap: the body is over MAX_RESPONSE_BYTES, not a stubbed exception.
            return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
        return httpx.Response(200, json=payload)

    src = _Src("https://job-boards.greenhouse.io/bigboard", "greenhouse", {"token": "bigboard"})
    with _client(handler) as c:
        vacs = GreenhouseStrategy().fetch(src, c)
    assert seen[0].endswith("/v1/boards/bigboard/jobs")
    assert "content=true" in seen[1]
    assert len(seen) == 2
    assert [v.external_id for v in vacs] == ["4001", "4002", "4003"]
    assert [v.title for v in vacs] == ["Research Engineer", "Policy Manager", "Recruiter"]
    assert vacs[0].location == "San Francisco, CA"
    assert vacs[0].department == "Research"
    assert all(v.description == "" for v in vacs)


def test_greenhouse_skips_content_when_the_board_is_over_the_detail_limit(monkeypatch):
    payload = json.loads(_fixture("greenhouse_light_list.json"))
    monkeypatch.setattr("app.scraper.greenhouse.GREENHOUSE_DETAIL_LIMIT", 2)
    seen: list[str] = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json=payload)

    src = _Src("https://boards.greenhouse.io/bigboard", "greenhouse", {"token": "bigboard"})
    with _client(handler) as c:
        vacs = GreenhouseStrategy().fetch(src, c)
    assert len(vacs) == 3
    assert all("content=true" not in url for url in seen)


def test_greenhouse_merges_content_for_a_small_board():
    payload = json.loads(_fixture("greenhouse_light_list.json"))
    rich_jobs = []
    for job in payload["jobs"][:2]:
        copied = dict(job)
        copied["content"] = "<p>Must have 5 years experience</p>"
        rich_jobs.append(copied)

    seen: list[str] = []

    def handler(request):
        seen.append(str(request.url))
        if "content=true" in str(request.url):
            return httpx.Response(200, json={"jobs": rich_jobs})
        return httpx.Response(200, json=payload)

    src = _Src("https://boards.greenhouse.io/bigboard", "greenhouse", {"token": "big board"})
    with _client(handler) as c:
        vacs = GreenhouseStrategy().fetch(src, c)
    assert seen[0].endswith("/v1/boards/big%20board/jobs")
    assert " " not in seen[0]
    by_id = {v.external_id: v for v in vacs}
    assert list(by_id) == ["4001", "4002", "4003"]
    assert "Must have 5 years experience" in by_id["4001"].description
    assert "Must have 5 years experience" in by_id["4002"].description
    assert by_id["4003"].description == ""


def test_lever_parser():
    def handler(request):
        return httpx.Response(200, json=[
            {"id": "abc", "text": "Data Analyst",
             "categories": {"location": "Cape Town", "team": "Analytics", "commitment": "Full-time"},
             "hostedUrl": "https://jobs.lever.co/acme/abc",
             "descriptionPlain": "Requirements\nSQL required\nPython advantageous"},
        ])
    src = _Src("https://jobs.lever.co/acme", "lever", {"token": "acme"})
    with _client(handler) as c:
        vacs = LeverStrategy().fetch(src, c)
    assert vacs[0].title == "Data Analyst"
    assert vacs[0].location == "Cape Town"
    assert vacs[0].employment_type == "Full-time"


def test_recruitee_parser():
    def handler(request):
        return httpx.Response(200, json={"offers": [
            {"id": 555, "title": "Finance Manager", "department": "Finance",
             "location": "Cape Town, South Africa", "employment_type_code": "fulltime_permanent",
             "remote": False, "hybrid": True, "published_at": "2026-08-01 09:00:00 UTC",
             "close_at": "2026-09-30 23:59:59 UTC",
             "description": "<p>Own the books.</p>",
             "careers_url": "https://acme.com/careers/finance-manager"},
        ]})
    src = _Src("https://acme.recruitee.com/careers", "recruitee", {"token": "acme"})
    with _client(handler) as c:
        vacs = RecruiteeStrategy().fetch(src, c)
    assert len(vacs) == 1
    v = vacs[0]
    assert v.title == "Finance Manager"
    assert v.external_id == "555"
    assert v.location == "Cape Town, South Africa"
    assert v.work_mode == "hybrid"
    assert v.closing_date == "2026-09-30 23:59:59 UTC"
    assert v.application_url == "https://acme.com/careers/finance-manager"


def test_workable_parser():
    def handler(request):
        return httpx.Response(200, json={"jobs": [
            {"shortcode": "ABC123", "title": "Backend Engineer", "department": "Engineering",
             "employment_type": "full_time",
             "location": {"city": "Johannesburg", "region": "Gauteng", "country": "South Africa",
                          "telecommuting": False},
             "published_on": "2026-07-15",
             "full_description": "<p>Build APIs.</p>",
             "url": "https://apply.workable.com/acme-inc/j/ABC123/",
             "shortlink": "https://acme.workable.com/j/ABC123"},
        ]})
    src = _Src("https://apply.workable.com/acme-inc/", "workable", {"token": "acme-inc"})
    with _client(handler) as c:
        vacs = WorkableStrategy().fetch(src, c)
    assert len(vacs) == 1
    v = vacs[0]
    assert v.title == "Backend Engineer"
    assert v.external_id == "ABC123"
    assert v.location == "Johannesburg, Gauteng, South Africa"
    assert v.application_url == "https://apply.workable.com/acme-inc/j/ABC123/"


def test_static_jsonld_parser():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"JobPosting","title":"Financial Accountant",
     "datePosted":"2026-07-15","validThrough":"2026-08-30",
     "employmentType":"FULL_TIME",
     "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress",
       "addressLocality":"Durban","addressCountry":"ZA"}},
     "description":"<ul><li>BCom required</li><li>CA(SA) advantageous</li></ul>",
     "url":"https://x.co.za/jobs/fa"}
    </script></head><body></body></html>
    """
    vacs = StaticHTMLStrategy().parse_html(html, source_url="https://x.co.za/careers")
    assert len(vacs) == 1
    v = vacs[0]
    assert v.title == "Financial Accountant"
    assert v.location == "Durban, ZA"
    assert v.employment_type == "FULL_TIME"
    assert v.application_url == "https://x.co.za/jobs/fa"


def test_static_parser_no_jsonld_returns_empty():
    assert StaticHTMLStrategy().parse_html("<html><body>No jobs here</body></html>") == []


def test_workday_parser_posts_cxs():
    payload = json.loads(_fixture("workday.json"))

    def handler(request: httpx.Request):
        assert request.method == "POST"
        assert request.url.path == "/wday/cxs/absa/ABSAcareersite/jobs"
        body = json.loads(request.content)
        assert body["offset"] == 0 and body["limit"] == 20 and body["appliedFacets"] == {}
        return httpx.Response(200, json=payload)

    src = _Src("https://absa.wd3.myworkdayjobs.com/ABSAcareersite", "workday", {
        "tenant": "absa", "site": "ABSAcareersite", "host": "absa.wd3.myworkdayjobs.com",
    })
    with _client(handler) as c:
        vacs = WorkdayStrategy().fetch(src, c)
    assert [v.title for v in vacs] == ["Account Manager", "Credit Analyst"]
    assert vacs[0].location == "Johannesburg"
    assert vacs[0].application_url.endswith("/ABSAcareersite/job/Johannesburg/Account-Manager_R1")


def test_workday_sends_country_facet_from_the_url():
    detected = detect_ats(
        "https://worldvision.wd1.myworkdayjobs.com/WorldVisionInternational?locationCountry=db69cf96446c11de98360015c5e6daf6"
    )
    assert detected[1]["facets"]["locationCountry"] == ["db69cf96446c11de98360015c5e6daf6"]
    payload = json.loads(_fixture("workday.json"))
    payload["total"] = 1
    payload["jobPostings"] = payload["jobPostings"][:1]

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["appliedFacets"]["locationCountry"] == ["db69cf96446c11de98360015c5e6daf6"]
        return httpx.Response(200, json=payload)

    src = _Src("https://worldvision.wd1.myworkdayjobs.com/WorldVisionInternational", "workday", detected[1])
    with _client(handler) as c:
        vacs = WorkdayStrategy().fetch(src, c)
    assert vacs[0].title == "Account Manager"


def test_oracle_parser_keeps_finder_commas():
    payload = json.loads(_fixture("oracle.json"))
    seen: list[str] = []

    def handler(request: httpx.Request):
        seen.append(str(request.url))
        return httpx.Response(200, json=payload)

    src = _Src(
        "https://fa.example.oraclecloud.com/hcmUI/CandidateExperience/en/sites/MrPriceGroupCareers/jobs",
        "oracle",
        {"host": "fa.example.oraclecloud.com", "site_number": "CX", "site_name": "MrPriceGroupCareers"},
    )
    with _client(handler) as c:
        vacs = OracleCEStrategy().fetch(src, c)
    assert "siteNumber=CX,limit=25,offset=0" in seen[0]
    assert "%2C" not in seen[0]
    assert vacs[0].title == "Financial Manager"
    assert vacs[0].location == "Durban, South Africa"
    assert vacs[0].closing_date == "2026-10-01"
    assert vacs[0].application_url.endswith("/sites/MrPriceGroupCareers/job/300000123")


def test_breezy_parser():
    payload = json.loads(_fixture("breezy.json"))

    def handler(request: httpx.Request):
        assert request.url.path == "/json"
        return httpx.Response(200, json=payload)

    src = _Src("https://isuzu.breezy.hr/", "breezy", {"token": "isuzu"})
    with _client(handler) as c:
        vacs = BreezyStrategy().fetch(src, c)
    assert vacs[0].title == "Area Manager"
    assert vacs[0].location == "Gqeberha"
    assert vacs[0].employment_type == "Full-Time"
    assert vacs[0].external_id == "a1b2"


def test_pinpoint_parser_clips_description():
    payload = json.loads(_fixture("pinpoint.json"))
    payload["data"][0]["description"] = "<p>" + ("word " * 2000) + "</p>"

    def handler(request: httpx.Request):
        assert request.url.path == "/postings.json"
        return httpx.Response(200, json=payload)

    src = _Src("https://kempinski.pinpointhq.com/", "pinpoint", {"host": "kempinski.pinpointhq.com"})
    with _client(handler) as c:
        vacs = PinpointStrategy().fetch(src, c)
    assert vacs[0].title == "Chef de Partie"
    assert vacs[0].closing_date == "2026-12-01T00:00:00Z"
    assert len(vacs[0].description) <= 4000
    assert vacs[0].raw == {"id": 9, "title": "Chef de Partie"}


def test_smartrecruiters_reads_saved_page():
    payload = json.loads(_fixture("smartrecruiters-page.json"))

    def handler(request: httpx.Request):
        assert "offset=0" in str(request.url)
        assert "country=" not in str(request.url)
        return httpx.Response(200, json=payload)

    src = _Src("https://careers.smartrecruiters.com/OUTsurance", "smartrecruiters", {"token": "OUTsurance"})
    with _client(handler) as c:
        vacs = SmartRecruitersStrategy().fetch(src, c)
    assert vacs[0].title == "Life Sales Advisor"
    assert vacs[0].location == "Pretoria, South Africa"
    bosch = detect_ats("https://careers.smartrecruiters.com/BoschGroup/south-africa")
    assert bosch[1]["token"] == "BoschGroup" and bosch[1]["country"] == "za"


ATNS = "https://atns.ci.hr/applicant/index.php?controller=Page&name=jobsearch"
_VIEW = "54e0dd96-197b-4502-b2d0-7afd6f1acd67"


def test_cihr_reads_atns_listings_fixture():
    page = _fixture("cihr_atns_page.js.txt")
    listings = _fixture("cihr_atns_listings.html")
    seen: list[str] = []

    def handler(request: httpx.Request):
        seen.append(str(request.url))
        if "controller=Listings" in str(request.url):
            assert "method=get" in str(request.url)
            assert "entity=listings" in str(request.url)
            assert f"viewid={_VIEW}" in str(request.url)
            assert "batch=1" in str(request.url)
            assert "batchsize=25" in str(request.url)
            assert "adapter=" in str(request.url)
            return httpx.Response(200, text=listings)
        return httpx.Response(200, text=page)

    src = _Src(ATNS, "cihr", {"host": "atns.ci.hr"})
    with _client(handler) as c:
        vacs = CihrStrategy().fetch(src, c)
    assert len(seen) == 2
    assert [v.title for v in vacs] == [
        "Head - ATM Planning and Technology adoption",
        "Manager Air Traffic Services: FALA",
    ]
    first, second = vacs
    assert first.external_id == "658d690a-ac5f-4b44-b547-abcfed4e0e32"
    assert first.location == "Southern Africa"
    assert first.employment_type == "Permanent"
    assert first.salary == "Market Related"
    assert first.department == "Transport, Logistics and Freight"
    assert first.closing_date == "7 October 2026"
    assert normalize_date(first.closing_date) == date(2026, 10, 7)
    assert first.description.startswith("To provide a strategic")
    assert "listingid=658d690a-ac5f-4b44-b547-abcfed4e0e32" in first.application_url
    assert first.application_url.startswith("https://atns.ci.hr/applicant/index.php")
    assert second.location == "Johannesburg"
    assert second.department == "Transport and Logistics Management"
    assert "Aviation & Aerospace" not in (first.department or "")


def test_cihr_empty_board_is_a_real_zero():
    page = _fixture("cihr_atns_page.js.txt")
    empty = '<div class="list-items-container adaptive-list" data-recordcount="0"></div>'

    def handler(request: httpx.Request):
        if "controller=Listings" in str(request.url):
            return httpx.Response(200, text=empty)
        return httpx.Response(200, text=page)

    src = _Src(ATNS, "cihr", {"host": "atns.ci.hr"})
    with _client(handler) as c:
        assert CihrStrategy().fetch(src, c) == []


def test_cihr_missing_widget_is_a_failure():
    src = _Src(ATNS, "cihr", {"host": "atns.ci.hr"})

    def handler(request: httpx.Request):
        return httpx.Response(200, text="<html><p>Welcome</p></html>")

    with _client(handler) as c:
        try:
            CihrStrategy().fetch(src, c)
        except ValueError as exc:
            assert "listings widget" in str(exc)
        else:
            raise AssertionError("expected a failure, not an empty list")


def test_cihr_missing_list_container_is_a_failure():
    page = _fixture("cihr_atns_page.js.txt")

    def handler(request: httpx.Request):
        if "controller=Listings" in str(request.url):
            return httpx.Response(200, text="<html>no list</html>")
        return httpx.Response(200, text=page)

    src = _Src(ATNS, "cihr", {"host": "atns.ci.hr"})
    with _client(handler) as c:
        try:
            CihrStrategy().fetch(src, c)
        except ValueError as exc:
            assert "no job list" in str(exc)
        else:
            raise AssertionError("expected a failure, not an empty list")


def test_cihr_follows_jobsearch_and_ignores_featured_cards():
    home = (
        '<a href="?controller=Listings&method=view&listingid=featured-only">Featured</a>'
        '<a href="?controller=Page&amp;name=jobsearch">All jobs</a>'
    )
    page = _fixture("cihr_atns_page.js.txt")
    listings = _fixture("cihr_atns_listings.html")
    seen: list[str] = []

    def handler(request: httpx.Request):
        url = str(request.url)
        seen.append(url)
        if "name=jobsearch" in url:
            return httpx.Response(200, text=page)
        if "controller=Listings" in url and "method=get" in url:
            return httpx.Response(200, text=listings)
        return httpx.Response(200, text=home)

    src = _Src("https://assmang.ci.hr", "cihr", {"host": "assmang.ci.hr"})
    with _client(handler) as c:
        vacs = CihrStrategy().fetch(src, c)
    assert len(vacs) == 2
    assert all("featured-only" not in (v.external_id or "") for v in vacs)
    assert any("name=jobsearch" in url for url in seen)
    assert any("batchsize=25" in url for url in seen)


def test_cihr_refuses_an_off_host_redirect():
    def handler(request: httpx.Request):
        if request.url.host == "wsucareers.ci.hr":
            return httpx.Response(302, headers={"location": "https://www.ci.hr/"})
        return httpx.Response(200, text="<html>vendor home</html>")

    src = _Src("https://wsucareers.ci.hr/applicant", "cihr", {"host": "wsucareers.ci.hr"})
    with _client(handler) as c:
        try:
            CihrStrategy().fetch(src, c)
        except ValueError as exc:
            assert "different host" in str(exc)
        else:
            raise AssertionError("off-host redirect must not become a vacancy list")


def test_cihr_paginates_until_recordcount_and_caps_batch_size():
    page = 'new List({ id:"listings-list", entity:"listings", viewId:"view-1", controller:"Listings", endpoint:"get", adapter:"", batchsize: 500 })'
    one = '''
    <div class="list-items-container" data-recordcount="2">
      <div class="dynamic-card view-data-row" id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1">
        <h5><a href="?controller=Listings&method=view&listingid=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1">First role</a></h5>
        <p>One</p>
        <b>Apply by:</b> 1 January 2027
        <b>Location</b>: Cape Town
      </div>
    </div>
    '''
    two = '''
    <div class="list-items-container" data-recordcount="2">
      <div class="dynamic-card view-data-row" id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2">
        <h5><a href="?controller=Listings&method=view&listingid=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2">Second role</a></h5>
      </div>
    </div>
    '''
    batches: list[str] = []

    def handler(request: httpx.Request):
        url = str(request.url)
        if "controller=Listings" not in url:
            return httpx.Response(200, text=page)
        batches.append(url)
        assert "batchsize=100" in url
        if "batch=1" in url:
            return httpx.Response(200, text=one)
        return httpx.Response(200, text=two)

    src = _Src(ATNS, "cihr", {"host": "atns.ci.hr"})
    with _client(handler) as c:
        vacs = CihrStrategy().fetch(src, c)
    assert [v.title for v in vacs] == ["First role", "Second role"]
    assert len(batches) == 2
    assert vacs[0].location == "Cape Town"
    assert vacs[0].closing_date == "1 January 2027"


def test_static_html_follows_rss_when_the_page_has_no_jobs():
    page = _fixture("careers-with-feed.html")
    feed = _fixture("jobs-feed.xml")

    def handler(request: httpx.Request):
        if request.url.path.endswith("feed.xml"):
            return httpx.Response(200, text=feed, headers={"content-type": "application/rss+xml"})
        return httpx.Response(200, text=page)

    src = _Src("https://example.co.za/careers", "static", {})
    with _client(handler) as c:
        vacs = StaticHTMLStrategy().fetch(src, c)
    assert [v.title for v in vacs] == ["Workshop Technician", "Graduate Intern"]
    assert vacs[0].application_url == "https://example.co.za/jobs/workshop-technician"


# ---- bot-challenge pages and news feeds (SA colleges and universities) -------

WAIT_PAGE = (
    "<!DOCTYPE html><html><head><title>One moment, please...</title>"
    "<style>body{font-family:sans-serif}</style></head><body><h1>One moment, please...</h1>"
    "<p>Please wait while your request is being verified...</p>"
    "<script>setTimeout(function(){ window.location.reload(true); }, 4000);</script></body></html>"
)


def test_wait_interstitial_is_a_bot_challenge_not_an_empty_list():
    import pytest
    from app.scraper.static_html import BotChallengeError, _is_wait_interstitial

    assert _is_wait_interstitial(WAIT_PAGE)
    # A real page that merely says something similar is not a challenge.
    assert not _is_wait_interstitial(
        "<html><head><title>Vacancies</title></head><body>One moment, please read our POPIA notice."
        "</body></html>")
    # A page with no reload script is not the challenge either.
    assert not _is_wait_interstitial("<html><head><title>One moment, please</title></head><body>hi</body></html>")

    src = _Src("https://college.example.ac.za/vacancies/", "static", {})
    with _client(lambda r: httpx.Response(200, text=WAIT_PAGE)) as c:
        with pytest.raises(BotChallengeError):
            StaticHTMLStrategy().fetch(src, c)


def test_page_that_says_no_vacancies_is_still_an_empty_list_not_a_challenge():
    page = "<html><head><title>Vacancies</title></head><body><p>No vacancies at this time.</p></body></html>"
    src = _Src("https://college.example.ac.za/vacancies/", "static", {})
    with _client(lambda r: httpx.Response(200, text=page)) as c:
        assert StaticHTMLStrategy().fetch(src, c) == []


NEWS_FEED = """<?xml version="1.0"?><rss version="2.0"><channel><title>College news</title>
<item><title>2026 SRC Elections at Seme Hall</title><link>https://college.example.ac.za/news/src</link></item>
<item><title>Heritage Month</title><link>https://college.example.ac.za/news/heritage</link></item>
<item><title>2026 Newsletter - Edition 2</title><link>https://college.example.ac.za/news/newsletter</link></item>
<item><title>Founder&#8217;s Annual Lecture to convene leaders on the future world of work</title><link>https://college.example.ac.za/news/lecture</link></item>
<item><title>International students welcomed at orientation</title><link>https://college.example.ac.za/news/intl</link></item>
</channel></rss>"""


def test_news_only_feed_is_not_read_as_vacancies():
    page = '<html><head><link rel="alternate" type="application/rss+xml" href="/feed/" /></head><body>Vacancies</body></html>'

    def handler(request: httpx.Request):
        if request.url.path == "/feed/":
            return httpx.Response(200, text=NEWS_FEED, headers={"content-type": "application/rss+xml"})
        return httpx.Response(200, text=page)

    src = _Src("https://college.example.ac.za/vacancies/", "static", {})
    with _client(handler) as c:
        assert StaticHTMLStrategy().fetch(src, c) == []
    assert StaticHTMLStrategy().parse_feed(NEWS_FEED, "https://college.example.ac.za/vacancies/") == []


def test_feed_keeps_only_the_items_that_read_like_vacancies():
    feed = NEWS_FEED.replace("</channel>", (
        "<item><title>Vacancy: Lecturer - Business Management</title><link>https://college.example.ac.za/v/1</link></item>"
        "<item><title>Applications invited for the post of Registrar</title><link>https://college.example.ac.za/v/2</link></item>"
        "</channel>"))
    titles = [v.title for v in StaticHTMLStrategy().parse_feed(feed, "https://college.example.ac.za/")]
    assert titles == ["Vacancy: Lecturer - Business Management",
                      "Applications invited for the post of Registrar"]
