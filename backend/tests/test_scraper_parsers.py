"""Parser tests against saved sample payloads (offline, via httpx.MockTransport)."""
import httpx

from app.scraper.base import detect_ats, html_to_text
from app.scraper.greenhouse import GreenhouseStrategy
from app.scraper.lever import LeverStrategy
from app.scraper.static_html import StaticHTMLStrategy


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
    assert detect_ats("https://www.goldfields.com/careers/")[0] == "static"


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
