"""Offline seed-page checks. The browser is a stand-in, never launched."""
import inspect

import httpx

from app.core.config import settings
from app.services.seed_page import fetch_seed_page, looks_like_js_shell


class _Renderer:
    def __init__(self):
        self.urls = []

    def render(self, url: str) -> str:
        self.urls.append(url)
        return "<html><title>Careers</title><body>Nurse vacancy in Nairobi</body></html>"


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_js_shell_is_rendered_only_when_a_renderer_is_passed():
    shell = "<html><body>Please enable JavaScript</body></html>"
    assert looks_like_js_shell(shell) is True

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, text="no", request=request)
        return httpx.Response(200, text=shell, request=request)

    renderer = _Renderer()
    with _client(handler) as client:
        plain = fetch_seed_page("https://careers.example.com/jobs", client)
        rendered = fetch_seed_page("https://careers.example.com/jobs", client, renderer=renderer)
    assert plain.rendered is False
    assert plain.html == shell
    assert rendered.rendered is True
    assert "Nurse vacancy" in rendered.html
    assert renderer.urls == ["https://careers.example.com/jobs"]


def test_a_listing_and_a_challenge_are_not_rendered():
    listing = '<html><script type="application/ld+json">{"@type":"JobPosting"}</script></html>'
    challenge = "<html><title>Just a moment...</title> cloudflare cf-challenge</html>"
    assert looks_like_js_shell(listing) is False
    assert looks_like_js_shell(challenge) is False

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, text="no", request=request)
        return httpx.Response(200, text=challenge, request=request)

    renderer = _Renderer()
    with _client(handler) as client:
        page = fetch_seed_page("https://careers.example.com/jobs", client, renderer=renderer)
    assert page.error == "bot_challenge"
    assert page.html == ""
    assert renderer.urls == []


def test_robots_disallow_skips_the_page_and_the_renderer():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n", request=request)
        return httpx.Response(200, text="Please enable JavaScript", request=request)

    renderer = _Renderer()
    with _client(handler) as client:
        page = fetch_seed_page("https://careers.example.com/jobs", client, renderer=renderer)
    assert page.robots_allowed is False
    assert page.error == "robots"
    assert seen == ["/robots.txt"]
    assert renderer.urls == []


def test_private_address_is_not_fetched_or_rendered():
    renderer = _Renderer()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, text="Please enable JavaScript", request=request)

    with _client(handler) as client:
        page = fetch_seed_page("http://127.0.0.1/careers", client, renderer=renderer)
    assert page.error == "private_ip"
    assert seen == []
    assert renderer.urls == []


def test_public_name_that_resolves_private_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr("app.scraper.ssrf._default_resolve", lambda _host: ["10.1.2.3"])
    renderer = _Renderer()

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(request.url)

    with _client(handler) as client:
        page = fetch_seed_page("https://careers.example.com/jobs", client, renderer=renderer)
    assert page.error == "dns_private"
    assert renderer.urls == []


def test_cron_url_check_stays_on_plain_http():
    from app.scheduler import jobs as cron_jobs
    from app.services import url_tester

    source = inspect.getsource(cron_jobs.test_all_urls)
    sync_source = inspect.getsource(url_tester.test_url_sync)
    assert "renderer" not in source
    assert "seed_page" not in source
    assert "renderer" not in sync_source
    assert "playwright" not in source.lower()
    assert "playwright" not in sync_source.lower()
