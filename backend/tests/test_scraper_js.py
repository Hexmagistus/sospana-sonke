"""Tests for JavaScript-rendered ATS coverage."""
import glob

import pytest

from app.core.config import settings
from app.scraper.base import detect_ats, get_strategy
from app.scraper.render import MockRenderer
from app.scraper.rendered_html import RenderedHTMLStrategy

JSONLD_PAGE = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"JobPosting","title":"Rendered Analyst",
 "datePosted":"2026-07-01","employmentType":"FULL_TIME",
 "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress",
   "addressLocality":"Cape Town","addressCountry":"ZA"}},
 "description":"<ul><li>SQL required</li></ul>","url":"https://x.co/jobs/1"}
</script></head><body></body></html>
"""


class _Src:
    def __init__(self, url):
        self.url = url
        self.config = {}


def test_detect_js_ats():
    assert detect_ats("https://acme.wd3.myworkdayjobs.com/careers")[0] == "js"
    assert detect_ats("https://career5.successfactors.eu/careers")[0] == "js"
    assert detect_ats("https://acme.taleo.net/careersection")[0] == "js"
    assert isinstance(get_strategy("js"), RenderedHTMLStrategy)


def test_rendered_strategy_parses_injected_jobs():
    strat = RenderedHTMLStrategy(renderer=MockRenderer(JSONLD_PAGE))
    vacs = strat.fetch(_Src("https://acme.myworkdayjobs.com/careers"), client=None)
    assert len(vacs) == 1
    assert vacs[0].title == "Rendered Analyst"
    assert vacs[0].location == "Cape Town, ZA"


def test_rendered_strategy_disabled_returns_empty(monkeypatch):
    # No injected renderer + global switch off -> no browser, empty result.
    monkeypatch.setattr(settings, "JS_RENDER_ENABLED", False)
    strat = RenderedHTMLStrategy()
    assert strat.fetch(_Src("https://acme.myworkdayjobs.com/careers"), client=None) == []


def test_live_js_render(monkeypatch):
    """A page that injects JSON-LD via JavaScript is read only after rendering."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    chrome = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    try:
        import playwright  # noqa: F401
    except Exception:
        pytest.skip("playwright not installed")
    if not chrome:
        pytest.skip("no chromium available")

    page = (b"<html><body><script>"
            b"document.addEventListener('DOMContentLoaded',function(){"
            b"var s=document.createElement('script');s.type='application/ld+json';"
            b"s.textContent=JSON.stringify({'@context':'https://schema.org','@type':'JobPosting',"
            b"'title':'JS Rendered Role','description':'x',"
            b"'jobLocation':{'@type':'Place','address':{'addressLocality':'Durban','addressCountry':'ZA'}},"
            b"'url':'http://x/jobs/9'});document.body.appendChild(s);});"
            b"</script></body></html>")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(page)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(settings, "JS_RENDER_ENABLED", True)
        monkeypatch.setattr(settings, "PLAYWRIGHT_EXECUTABLE_PATH", chrome[0])
        from app.scraper.render import PlaywrightRenderer
        from app.scraper.static_html import StaticHTMLStrategy

        url = f"http://127.0.0.1:{port}/"
        # Raw (unrendered) HTML has no JobPosting; rendering reveals it.
        import httpx
        raw = httpx.get(url).text
        assert StaticHTMLStrategy().parse_html(raw) == []
        try:
            rendered = PlaywrightRenderer().render(url)
        except Exception as e:
            pytest.skip(f"browser launch failed: {e}")
        vacs = StaticHTMLStrategy().parse_html(rendered, source_url=url)
        assert len(vacs) == 1 and vacs[0].title == "JS Rendered Role"
        assert vacs[0].location == "Durban, ZA"
    finally:
        server.shutdown()
