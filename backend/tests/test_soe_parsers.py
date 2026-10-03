"""State-owned-entity career sites: Cornerstone (Transnet), PeopleSoft (CSIR),
MCI Direct Hire (ARC, SACAA, Magalies...), simplify.hr (HWSETA, NAMC, SANBI...)
and the generic JobPosting JSON-LD reader.

Everything runs offline. The fixtures under ``fixtures/scraper`` are real
responses fetched on 2026-10-03, with session ids and the anonymous Cornerstone
token redacted. Tests that need a case the live sites did not show (a second
page, a count that does not add up) change a fixture in the test and say so.
"""
import json
import re
from pathlib import Path

import httpx
import pytest

from app.models.company import Company
from app.models.vacancy import Vacancy
from app.scraper.base import detect_ats, get_strategy
from app.scraper.cornerstone import CornerstoneStrategy
from app.scraper.extract import normalize_date
from app.scraper.jsonld import parse_job_postings
from app.scraper.mci import MciStrategy
from app.scraper.peoplesoft import PeopleSoftStrategy
from app.scraper.simplify import SimplifyStrategy
from app.scraper.static_html import StaticHTMLStrategy
from app.services.scan_service import ensure_source, scan_source
from app.services.vacancy_counts import companies_with_known_vacancy_count

_FIXTURES = Path(__file__).parent / "fixtures" / "scraper"


def _fx(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


class _Src:
    def __init__(self, url, ats_type="", config=None):
        self.url, self.ats_type, self.config = url, ats_type, config or {}


BOT_UA = "SospanaSonkeBot/0.1 (+https://sospanasonke.co.za/bot)"


def _client(handler):
    # The scanner builds its client with the honest bot agent (scan_service).
    return httpx.Client(transport=httpx.MockTransport(handler), headers={"User-Agent": BOT_UA})


# ---- detection --------------------------------------------------------------

def test_detect_ats_for_soe_platforms():
    csod = detect_ats("https://transnettalentportal.csod.com/ux/ats/careersite/1/home?c=transnettalentportal")
    assert csod == ("cornerstone", {"host": "transnettalentportal.csod.com", "career_site_id": "1"})
    # A csod.com URL that is not a career site is not guessed at.
    assert detect_ats("https://transnettalentportal.csod.com/")[0] == "static"
    assert detect_ats("https://arcjobs.mcidirecthire.com/Vacancy")[0] == "mci"
    assert detect_ats("https://sacaa.mcidirecthire.com/External/CurrentOpportunities")[0] == "mci"
    assert detect_ats("https://bqajobs.mcidirecthire.com/")[0] == "mci"
    # "Job Central" is a different product.
    assert detect_ats("https://jobs.mcidirecthire.com/AvailableVacancies/Index?CompanyName=cipc")[0] == "static"
    assert detect_ats("https://namc.simplify.hr/")[0] == "simplify"
    assert detect_ats("https://www.simplify.hr/")[0] == "static"
    assert detect_ats("https://candidate.csir.co.za/")[0] == "peoplesoft"
    assert detect_ats(
        "https://hr.example.org/psc/hr/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?FOCUS=Applicant"
    )[0] == "peoplesoft"
    # Look-alikes do not match.
    assert detect_ats("https://careers.example.com/csod.com/ux/ats/careersite/1")[0] == "static"
    assert detect_ats("https://example.com/mcidirecthire.com")[0] == "static"
    # SuccessFactors is still browser-only (and its robots.txt disallows crawling).
    assert detect_ats("https://career2.successfactors.eu/career?company=southafr01")[0] == "js"
    for kind in ("cornerstone", "mci", "peoplesoft", "simplify"):
        assert get_strategy(kind).ats_type == kind


# ---- Cornerstone (Transnet) -------------------------------------------------

TRANSNET = "https://transnettalentportal.csod.com/ux/ats/careersite/1/home"
API = "https://uk.api.csod.com/rec-job-search/external/jobs"


def _csod_handler(payloads, seen=None):
    page = _fx("cornerstone_transnet_page.html")

    def handler(request: httpx.Request):
        if seen is not None:
            seen.append(request)
        if str(request.url) == TRANSNET:
            return httpx.Response(200, text=page)
        if str(request.url) == API:
            body = json.loads(request.content)
            return httpx.Response(200, json=payloads[body["pageNumber"] - 1])
        return httpx.Response(404)
    return handler


def test_cornerstone_reads_transnet_job_list():
    seen: list[httpx.Request] = []
    payload = json.loads(_fx("cornerstone_transnet_jobs.json"))
    src = _Src(TRANSNET, "cornerstone", {"host": "transnettalentportal.csod.com", "career_site_id": "1"})
    with _client(_csod_handler([payload], seen)) as c:
        vacs = CornerstoneStrategy().fetch(src, c)
    assert len(vacs) == 8 == payload["data"]["totalCount"]
    assert len(seen) == 2
    post = seen[1]
    assert post.headers["authorization"] == "Bearer REDACTED-ANONYMOUS-TOKEN"
    body = json.loads(post.content)
    assert body["careerSiteId"] == 1 and body["pageNumber"] == 1 and body["searchText"] == ""
    first = vacs[0]
    assert first.external_id == "5986"
    assert first.title.startswith("Work Integrated Technical Learner - Plumber")
    assert first.location == "ZA"
    assert first.posting_date == "2026-10-02" and first.closing_date == "2026-10-13"
    assert normalize_date(first.closing_date).isoformat() == "2026-10-13"
    assert first.application_url == (
        "https://transnettalentportal.csod.com/ux/ats/careersite/1/home/requisition/5986"
        "?c=transnettalentportal")
    by_id = {v.external_id: v for v in vacs}
    assert by_id["5921"].title == "Helicopter Night Captain"
    assert by_id["5921"].location == "Richards Bay, ZA"
    assert by_id["5965"].location == "Johannesburg, ZA"
    assert by_id["5965"].description.startswith("To coordinate and supervise")


def test_cornerstone_second_page_and_short_read():
    payload = json.loads(_fx("cornerstone_transnet_jobs.json"))
    reqs = payload["data"]["requisitions"]
    # Synthetic: 30 roles over two pages of 25 + 5 (the live board has 8).
    many = [dict(reqs[i % 8], requisitionId=9000 + i) for i in range(30)]
    pages = [
        {"data": {"totalCount": 30, "requisitions": many[:25]}},
        {"data": {"totalCount": 30, "requisitions": many[25:]}},
    ]
    src = _Src(TRANSNET, "cornerstone", {"host": "transnettalentportal.csod.com", "career_site_id": "1"})
    with _client(_csod_handler(pages)) as c:
        assert len(CornerstoneStrategy().fetch(src, c)) == 30
    # Total says 30 but only 25 can be read: fail, never report 25 as the count.
    short = [pages[0], {"data": {"totalCount": 30, "requisitions": []}}]
    with _client(_csod_handler(short)) as c, pytest.raises(ValueError, match="30 roles"):
        CornerstoneStrategy().fetch(src, c)


def test_cornerstone_zero_is_a_real_zero_and_garbage_is_not():
    src = _Src(TRANSNET, "cornerstone", {})
    empty = {"data": {"totalCount": 0, "requisitions": []}}
    with _client(_csod_handler([empty])) as c:
        assert CornerstoneStrategy().fetch(src, c) == []
    for bad in ({"data": None}, {"status": "Error"}, {"data": {"requisitions": []}}):
        with _client(_csod_handler([bad])) as c, pytest.raises(ValueError):
            CornerstoneStrategy().fetch(src, c)


def test_cornerstone_never_sends_the_token_off_csod():
    page = _fx("cornerstone_transnet_page.html").replace(
        "https://uk.api.csod.com/", "https://evil.example.com/")
    calls: list[str] = []

    def handler(request: httpx.Request):
        calls.append(str(request.url))
        return httpx.Response(200, text=page)

    with _client(handler) as c, pytest.raises(ValueError, match="csod.com"):
        CornerstoneStrategy().fetch(_Src(TRANSNET, "cornerstone", {}), c)
    assert calls == [TRANSNET]


def test_cornerstone_page_without_context_is_a_failure():
    with _client(lambda r: httpx.Response(200, text="<html>nothing</html>")) as c:
        with pytest.raises(ValueError, match="csod.context"):
            CornerstoneStrategy().fetch(_Src(TRANSNET, "cornerstone", {}), c)


# ---- PeopleSoft (CSIR) ------------------------------------------------------

CSIR = "https://candidate.csir.co.za/"
CSIR_FORM = "https://candidate.csir.co.za/psc/hr/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL"


def _csir_handler(results, seen):
    page = _fx("peoplesoft_csir_search_page.html")

    def handler(request: httpx.Request):
        seen.append(request)
        url = str(request.url)
        if request.method == "GET" and "/psp/hr/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL" in url:
            return httpx.Response(302, headers={"location": CSIR_FORM + "?FOCUS=Applicant"})
        if request.method == "GET":
            return httpx.Response(200, text=page)
        if request.method == "POST" and url == CSIR_FORM:
            return httpx.Response(200, text=results)
        return httpx.Response(404)
    return handler


def test_peoplesoft_reads_csir_results():
    seen: list[httpx.Request] = []
    with _client(_csir_handler(_fx("peoplesoft_csir_results.html"), seen)) as c:
        vacs = PeopleSoftStrategy().fetch(_Src(CSIR, "peoplesoft", {}), c)
    assert [v.title for v in vacs] == [
        "Researcher (One-year contract)",
        "Technologist: Cosmetics Lab",
        "Manager: Hosted National Programmes (Five -Year Contract)",
    ]
    post = seen[-1]
    form = dict(re.findall(r"([^&=]+)=([^&]*)", post.content.decode()))
    assert form["ICAction"] == "HRS_SCH_WRK_FLU_HRS_SEARCH_BTN"
    assert form["ICSID"] and form["ICStateNum"] == "1"
    # Honest agent only: no browser-style shim on either request.
    assert all(r.headers["user-agent"] == BOT_UA for r in seen)
    assert not any("mozilla" in r.headers["user-agent"].lower() for r in seen)
    first = vacs[0]
    assert first.external_id == "315144"
    assert first.location == "Durban (On-site)"
    assert first.department == "BT Biorefinery"
    assert first.posting_date == "30/09/2026" and first.closing_date == "07/10/2026"
    assert normalize_date(first.closing_date).isoformat() == "2026-10-07"
    assert first.raw["cluster"] == "Chemicals"
    assert "JobOpeningId=315144" in first.application_url
    assert first.application_url.startswith(
        "https://candidate.csir.co.za/psc/hr/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?Page=HRS_APP_JBPST_FL")


def test_peoplesoft_count_must_match_rows():
    results = _fx("peoplesoft_csir_results.html")
    with _client(_csir_handler(results.replace("<b>3</b> jobs found", "<b>7</b> jobs found"), [])) as c:
        with pytest.raises(ValueError, match="7 jobs"):
            PeopleSoftStrategy().fetch(_Src(CSIR, "peoplesoft", {}), c)
    # No statement of a count at all is unreadable, not zero.
    with _client(_csir_handler("<html><body>Unsupported Browser</body></html>", [])) as c:
        with pytest.raises(ValueError, match="how many"):
            PeopleSoftStrategy().fetch(_Src(CSIR, "peoplesoft", {}), c)


def test_peoplesoft_unsupported_browser_page_fails_the_scan():
    """If the site turns the honest bot away, nothing is counted (card stays 'Not counted yet')."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(200, text="<html><body>Unsupported Browser</body></html>")

    with _client(handler) as c:
        with pytest.raises(ValueError, match="no search form"):
            PeopleSoftStrategy().fetch(_Src(CSIR, "peoplesoft", {}), c)
    assert len(seen) == 1 and seen[0].headers["user-agent"] == BOT_UA


def test_peoplesoft_explicit_zero():
    with _client(_csir_handler("<html><body><b>0</b> jobs found.</body></html>", [])) as c:
        assert PeopleSoftStrategy().fetch(_Src(CSIR, "peoplesoft", {}), c) == []


def test_peoplesoft_form_must_stay_on_host():
    page = _fx("peoplesoft_csir_search_page.html").replace(
        "https://candidate.csir.co.za/psc", "https://evil.example.com/psc")
    with _client(lambda r: httpx.Response(200, text=page)) as c:
        with pytest.raises(ValueError, match="different host"):
            PeopleSoftStrategy().fetch(_Src(CSIR, "peoplesoft", {}), c)


# ---- MCI Direct Hire --------------------------------------------------------

def test_mci_vacancy_generation_arc():
    seen: list[str] = []

    def handler(request: httpx.Request):
        url = str(request.url)
        seen.append(url)
        if url == "https://arcjobs.mcidirecthire.com/Vacancy":
            return httpx.Response(200, text=_fx("mci_arc_page.html"))
        if url.startswith("https://arcjobs.mcidirecthire.com/Vacancy/Vacancies?"):
            assert "PageNumber=1" in url
            return httpx.Response(200, text=_fx("mci_arc_vacancies.html"))
        return httpx.Response(404)

    with _client(handler) as c:
        vacs = MciStrategy().fetch(_Src("https://arcjobs.mcidirecthire.com/Vacancy", "mci", {}), c)
    assert len(vacs) == 1
    v = vacs[0]
    assert v.title == "SENIOR RESEARCHER - AGRONOMY"
    assert v.external_id == "ARC-GC 77"
    assert v.location == "Potchefstroom"
    assert v.posting_date == "2026-05-04"
    assert v.department == "Research, 05 - GCI"
    assert v.description.startswith("The ARC-Grain Crops seeks to appoint")
    assert v.application_url.startswith("https://arcjobs.mcidirecthire.com/Vacancy/ViewDetails?parameters=")


def test_mci_vacancy_generation_empty_body_is_the_sites_own_zero():
    def handler(request: httpx.Request):
        if request.url.path == "/Vacancy":
            return httpx.Response(200, text=_fx("mci_arc_page.html"))
        return httpx.Response(200, text=_fx("mci_magalies_vacancies_empty.html"))

    with _client(handler) as c:
        src = _Src("https://magalieswaterjobs.mcidirecthire.com/Vacancy", "mci", {})
        assert MciStrategy().fetch(src, c) == []


def test_mci_vacancy_generation_pages_and_failures():
    page1 = _fx("mci_arc_vacancies.html").replace("totalPages: 1", "totalPages: 2")
    page2 = page1.replace("SENIOR RESEARCHER - AGRONOMY", "TECHNICIAN - SOIL").replace("ARC-GC 77", "ARC-GC 78")

    def make(second):
        def handler(request: httpx.Request):
            if request.url.path == "/Vacancy":
                return httpx.Response(200, text=_fx("mci_arc_page.html"))
            return httpx.Response(200, text=page1 if "PageNumber=1" in str(request.url) else second)
        return handler

    src = _Src("https://arcjobs.mcidirecthire.com/Vacancy", "mci", {})
    with _client(make(page2)) as c:
        assert [v.title for v in MciStrategy().fetch(src, c)] == [
            "SENIOR RESEARCHER - AGRONOMY", "TECHNICIAN - SOIL"]
    # The second page vanishing is a failure, not "1 vacancy".
    with _client(make("")) as c, pytest.raises(ValueError, match="part-way"):
        MciStrategy().fetch(src, c)
    # A body with cards but no page total is unreadable.
    nototal = _fx("mci_arc_vacancies.html").replace("totalPages", "pages")
    with _client(make(nototal)) as c:
        with pytest.raises(ValueError):
            MciStrategy().fetch(src, c)


def test_mci_external_generation_sacaa():
    posts: list[httpx.Request] = []

    def handler(request: httpx.Request):
        url = str(request.url)
        if request.method == "POST":
            posts.append(request)
            assert url == "https://sacaa.mcidirecthire.com/External/Search1?JobBoard=default"
            return httpx.Response(200, text=_fx("mci_sacaa_search.html"))
        if request.url.path == "/External/CurrentOpportunities":
            return httpx.Response(200, text=_fx("mci_sacaa_page.html"))
        return httpx.Response(200, text="<html>no vacancy list</html>")

    src = _Src("https://sacaa.mcidirecthire.com/External/CurrentOpportunities", "mci", {})
    with _client(handler) as c:
        vacs = MciStrategy().fetch(src, c)
    assert [v.external_id for v in vacs] == ["489", "488", "487", "465"]
    assert vacs[0].title == "International Relations Officer (2 years Fixed Term Contract)"
    assert vacs[1].title == "Compliance Officer: PAIA & POPIA"
    assert vacs[0].location == "Centurion"
    assert vacs[0].posting_date == "2026-09-29"
    assert vacs[0].description.startswith("The SACAA has an exciting opportunity")
    assert vacs[0].application_url.startswith("https://sacaa.mcidirecthire.com/External/Job?ref=")
    assert len(posts) == 1
    form = posts[0].content.decode()
    assert "HiddenQuerystring=TEkBhDYErs0qhHgue" in form and "pageNum=1" in form


def test_mci_external_generation_count_must_add_up():
    def handler_for(body):
        def handler(request: httpx.Request):
            if request.method == "POST":
                return httpx.Response(200, text=body)
            return httpx.Response(200, text=_fx("mci_sacaa_page.html"))
        return handler

    src = _Src("https://sacaa.mcidirecthire.com/External/CurrentOpportunities", "mci", {})
    listing = _fx("mci_sacaa_search.html")
    # Synthetic: the page claims 6 roles but shows 4.
    with _client(handler_for(listing.replace("var ListCounter = 4;", "var ListCounter = 6;"))) as c:
        with pytest.raises(ValueError, match="6 roles"):
            MciStrategy().fetch(src, c)
    # Synthetic: ListCounter 0 is the board's own zero.
    zero = "<div id=\"divlazyjobview\"></div><script>var ListCounter = 0;</script>"
    with _client(handler_for(zero)) as c:
        assert MciStrategy().fetch(src, c) == []
    # No stated total: unreadable.
    with _client(handler_for("<html>error</html>")) as c, pytest.raises(ValueError, match="total"):
        MciStrategy().fetch(src, c)


def test_mci_unknown_page_and_foreign_redirect_fail():
    src = _Src("https://x.mcidirecthire.com/", "mci", {})
    with _client(lambda r: httpx.Response(200, text="<html>Account/SystemError</html>")) as c:
        with pytest.raises(ValueError, match="no vacancy list"):
            MciStrategy().fetch(src, c)
    with _client(lambda r: httpx.Response(302, headers={"location": "https://other.example.com/"})) as c:
        with pytest.raises((ValueError, httpx.HTTPError)):
            MciStrategy().fetch(src, c)


# ---- simplify.hr ------------------------------------------------------------

def _simplify_handler(host, fragment, seen=None):
    def handler(request: httpx.Request):
        if seen is not None:
            seen.append(str(request.url))
        if request.url.path == "/":
            return httpx.Response(200, text=_fx("simplify_namc_home.html"))
        if request.url.path == "/vacancy/vacancies":
            return httpx.Response(200, text=fragment)
        return httpx.Response(404)
    return handler


def test_simplify_real_zero_and_real_lists():
    seen: list[str] = []
    with _client(_simplify_handler("namc", _fx("simplify_namc_vacancies.html"), seen)) as c:
        assert SimplifyStrategy().fetch(_Src("https://namc.simplify.hr/", "simplify", {}), c) == []
    assert seen[-1] == "https://namc.simplify.hr/vacancy/vacancies?query=&displayOrder=0"
    with _client(_simplify_handler("vaal", _fx("simplify_vaalcentralwater_vacancies.html"))) as c:
        assert SimplifyStrategy().fetch(_Src("https://vaalcentralwater.simplify.hr/", "simplify", {}), c) == []

    with _client(_simplify_handler("sanbi", _fx("simplify_sanbi_vacancies.html"))) as c:
        vacs = SimplifyStrategy().fetch(_Src("https://sanbi.simplify.hr/", "simplify", {}), c)
    assert [(v.external_id, v.title) for v in vacs] == [
        ("205122", "Administrative Officer"),
        ("204739", "Senior Project Officer: Biological Risk Analysis"),
    ]
    assert vacs[0].location == "Pretoria, Gauteng"
    assert vacs[0].posting_date == "30 September 2026"
    assert normalize_date(vacs[0].closing_date).isoformat() == "2026-10-16"
    assert vacs[0].application_url == "https://sanbi.simplify.hr/Vacancy/205122"

    with _client(_simplify_handler("hwseta", _fx("simplify_hwseta_vacancies.html"))) as c:
        vacs = SimplifyStrategy().fetch(_Src("https://hwseta.simplify.hr/", "simplify", {}), c)
    assert len(vacs) == 1 and vacs[0].title == "PROVIDER ACCREDITATION OFFICER"
    assert vacs[0].location == "Johannesburg, Gauteng"
    assert vacs[0].closing_date is None


def test_simplify_reads_absolute_vacancy_links():
    """The IIE group's tenants link https://{tenant}.Simplify.hr/Vacancy/N, not /Vacancy/N."""
    fragment = _fx("simplify_sanbi_vacancies.html").replace(
        'href="/Vacancy/', 'href="https://rbi.Simplify.hr/Vacancy/')
    assert "https://rbi.Simplify.hr/Vacancy/205122" in fragment
    with _client(_simplify_handler("rbi", fragment)) as c:
        vacs = SimplifyStrategy().fetch(_Src("https://rbi.simplify.hr/", "simplify", {}), c)
    assert [(v.external_id, v.title) for v in vacs] == [
        ("205122", "Administrative Officer"),
        ("204739", "Senior Project Officer: Biological Risk Analysis"),
    ]
    # The link always points at the tenant being scanned, whatever host the markup names.
    assert vacs[0].application_url == "https://rbi.simplify.hr/Vacancy/205122"


def test_simplify_unreadable_fragment_is_not_zero():
    with _client(_simplify_handler("x", "<html><body>Server busy</body></html>")) as c:
        with pytest.raises(ValueError, match="not readable"):
            SimplifyStrategy().fetch(_Src("https://x.simplify.hr/", "simplify", {}), c)
    # A home page that is not a simplify.hr company shell is a failure too.
    with _client(lambda r: httpx.Response(200, text="<html>hi</html>")) as c:
        with pytest.raises(ValueError, match="no vacancy list"):
            SimplifyStrategy().fetch(_Src("https://x.simplify.hr/", "simplify", {}), c)
    with pytest.raises(ValueError):
        SimplifyStrategy().fetch(_Src("https://example.com/", "simplify", {}), _client(lambda r: None))


# ---- CareerInHR on an employer's own domain ----------------------------------

def test_cihr_on_a_verified_custom_domain_only():
    assert detect_ats("https://jobs.uj.ac.za/applicant/index.php") == ("cihr", {"host": "jobs.uj.ac.za"})
    assert detect_ats("https://JOBS.UJ.AC.ZA/")[0] == "cihr"
    # Only the exact verified host: look-alikes and other subdomains are not guessed at.
    assert detect_ats("https://jobs.uj.ac.za.evil.example/")[0] == "static"
    assert detect_ats("https://www.uj.ac.za/jobs")[0] == "static"
    assert detect_ats("https://other.ac.za/")[0] == "static"


# ---- JSON-LD ----------------------------------------------------------------

def _ld(*blocks):
    return "".join(f'<script type="application/ld+json">{b}</script>' for b in blocks)


def test_jsonld_graph_itemlist_and_lists():
    page = _ld(
        json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "Organization", "name": "Acme"},
            {"@type": "JobPosting", "title": "Engineer", "identifier": {"@type": "PropertyValue", "value": "E-1"},
             "jobLocation": [
                 {"address": {"addressLocality": "Cape Town", "addressRegion": "WC", "addressCountry": "ZA"}},
                 {"address": {"addressLocality": "Durban", "addressCountry": {"name": "South Africa"}}}],
             "url": "/jobs/e-1"}]}),
        json.dumps({"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "item": {"@type": "schema:JobPosting", "title": "Clerk",
                                                            "identifier": 77}}]}),
        json.dumps([{"@type": ["JobPosting"], "title": "Driver", "employmentType": ["FULL_TIME", "CONTRACTOR"]}]),
    )
    vacs = parse_job_postings(page, "https://x.co.za/careers")
    assert [v.title for v in vacs] == ["Engineer", "Clerk", "Driver"]
    assert vacs[0].external_id == "E-1"
    assert vacs[0].location == "Cape Town, WC, ZA; Durban, South Africa"
    assert vacs[0].application_url == "https://x.co.za/jobs/e-1"
    assert vacs[1].external_id == "77"
    assert vacs[2].employment_type == "FULL_TIME, CONTRACTOR"


def test_jsonld_fields_and_noise():
    page = _ld(
        '{"@type":"JobPosting","title":"Analyst &amp; Planner","description":"&lt;p&gt;Do work&lt;/p&gt;&lt;ul&gt;&lt;li&gt;BCom&lt;/li&gt;&lt;/ul&gt;",'
        '"jobLocationType":"TELECOMMUTE","baseSalary":{"@type":"MonetaryAmount","currency":"ZAR",'
        '"value":{"@type":"QuantitativeValue","minValue":20000,"maxValue":30000,"unitText":"MONTH"}},'
        '"datePosted":"2026-09-01","validThrough":"2026-10-30"}',
        "{not json",
        '{"@type":"JobPosting"}',                       # no title: dropped
        '{"@type":"JobPosting","title":"Analyst &amp; Planner"}',   # same posting again: de-duplicated
    )
    vacs = parse_job_postings(page, "https://x.co.za/careers")
    assert len(vacs) == 1
    v = vacs[0]
    assert v.title == "Analyst & Planner"
    assert v.work_mode == "remote"
    assert v.salary == "ZAR 20000-30000 MONTH"
    assert "Do work" in v.description and "BCom" in v.description and "<" not in v.description
    assert v.posting_date == "2026-09-01" and v.closing_date == "2026-10-30"
    assert v.application_url == "https://x.co.za/careers"
    assert parse_job_postings("<html><body>No jobs</body></html>") == []
    assert parse_job_postings(_ld('{"@type":"Organization","name":"X"}')) == []


def test_static_strategy_uses_the_jsonld_reader():
    page = _ld('{"@type":"JobPosting","title":"Plumber","jobLocation":{"address":{"addressLocality":"Pretoria"}}}')
    vacs = StaticHTMLStrategy().parse_html(page, source_url="https://x.co.za/careers")
    assert [(v.title, v.location) for v in vacs] == [("Plumber", "Pretoria")]


# ---- scan integration -------------------------------------------------------

def _company(db, name, url):
    company = Company(company_name=name, country="South Africa", source_type="SOE",
                      careers_url=url, scraping_status="pending", active=True)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def test_scan_stores_roles_and_marks_the_count_known(db):
    company = _company(db, "SACAA", "https://sacaa.mcidirecthire.com/External/CurrentOpportunities")
    source = ensure_source(db, company)
    assert source.ats_type == "mci"

    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(200, text=_fx("mci_sacaa_search.html"))
        return httpx.Response(200, text=_fx("mci_sacaa_page.html"))

    with _client(handler) as c:
        report = scan_source(db, source, client=c)
    assert report.status == "ok" and report.created == 4
    assert db.query(Vacancy).filter(Vacancy.company_id == company.id, Vacancy.is_open.is_(True)).count() == 4
    assert source.parser_used == "mci" and source.scraper_status == "SUCCESS"
    assert company.id in companies_with_known_vacancy_count(db, [company.id])


def test_scan_zero_from_simplify_is_known_but_unreadable_stays_unknown(db):
    empty = _company(db, "NAMC", "https://namc.simplify.hr/")
    broken = _company(db, "Broken", "https://broken.simplify.hr/")
    e_src, b_src = ensure_source(db, empty), ensure_source(db, broken)

    def handler(request: httpx.Request):
        host = request.url.host
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/":
            return httpx.Response(200, text=_fx("simplify_namc_home.html"))
        if host == "namc.simplify.hr":
            return httpx.Response(200, text=_fx("simplify_namc_vacancies.html"))
        return httpx.Response(200, text="<html>maintenance</html>")

    with _client(handler) as c:
        scan_source(db, e_src, client=c)
        scan_source(db, b_src, client=c)
    assert e_src.scraper_status == "NO_VACANCIES" and e_src.parser_used == "simplify"
    assert b_src.last_success_at is None
    known = companies_with_known_vacancy_count(db, [empty.id, broken.id])
    assert known == {empty.id}


def test_normalize_date_reads_long_month_names():
    # Previously cut to "16 October 202" and returned None.
    assert normalize_date("16 October 2026").isoformat() == "2026-10-16"
    assert normalize_date("30 September 2026").isoformat() == "2026-09-30"
    assert normalize_date("7 October 2026").isoformat() == "2026-10-07"
    assert normalize_date("2026-08-30T10:00:00+02:00").isoformat() == "2026-08-30"
