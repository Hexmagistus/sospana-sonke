"""Fetch a public careers page for offline seed work.

The daily ``test_all_urls`` job and ``test_url`` stay on plain HTTP. This
module is for scripts that verify or discover seed rows. A renderer is
optional: the caller passes one only after installing a browser, and only a
JavaScript shell is rendered. Bot-challenge pages are not rendered.

Every fetch is checked against robots.txt and the SSRF rules before the
response is kept. The renderer is not called unless those checks have already
passed for the final URL.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.scraper.politeness import RobotsChecker, is_aws_waf_challenge, request_with_backoff
from app.scraper.ssrf import SsrfBlocked

_SHELL_PHRASES = (
    "enable javascript",
    "javascript is required",
    "javascript is disabled",
    "please turn on javascript",
    "you need to enable javascript",
    "this page requires javascript",
)
_ROOT = re.compile(r"""id=["'](?:root|app|__next|___gatsby)["']""", re.I)
_SCRIPT = re.compile(r"<script[\s\S]*?</script>", re.I)
_STYLE = re.compile(r"<style[\s\S]*?</style>", re.I)
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class SeedPage:
    url: str
    ok: bool
    status_code: int | None
    final_url: str | None
    html: str
    rendered: bool
    robots_allowed: bool | None
    error: str | None


def visible_text(html: str) -> str:
    text = _STYLE.sub(" ", _SCRIPT.sub(" ", html or ""))
    text = _TAG.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_bot_challenge(html: str) -> bool:
    """A wall asking the client to prove it is human. Not a vacancy list."""
    low = (html or "").lower()
    if any(marker in low for marker in ("awswaf", "aws-waf", "gokuprops", "cf-challenge", "cf-browser-verification", "/cdn-cgi/challenge")):
        return True
    if "just a moment" in low and "cloudflare" in low:
        return True
    if "hcaptcha.com" in low or "g-recaptcha" in low or "recaptcha/api" in low:
        return True
    return False


def looks_like_js_shell(html: str) -> bool:
    """True when the HTTP body is an empty client-rendered shell.

    A page that already names a posting, and a bot challenge, are both false:
    the first needs no browser, and the second must not be executed.
    """
    if not html or len(html) > 1_500_000:
        return False
    if is_bot_challenge(html):
        return False
    low = html.lower()
    if "jobposting" in low:
        return False
    text = visible_text(html)
    if any(phrase in low for phrase in _SHELL_PHRASES) and len(text) < 2500:
        return True
    if _ROOT.search(html) and len(text) < 500:
        return True
    return False


def fetch_seed_page(url: str, client: httpx.Client, renderer=None) -> SeedPage:
    """GET ``url``. Render only when ``renderer`` is set and the body is a shell.

    ``renderer`` is any object with ``render(url) -> str``. This function never
    constructs a browser.
    """
    empty = SeedPage(url, False, None, None, "", False, None, None)
    try:
        from app.scraper.ssrf import assert_safe_fetch_url
        assert_safe_fetch_url(url)
    except SsrfBlocked as exc:
        return SeedPage(url, False, None, None, "", False, None, exc.verdict)

    robots = RobotsChecker(client)
    try:
        allowed = robots.is_allowed(url)
    except SsrfBlocked as exc:
        return SeedPage(url, False, None, None, "", False, None, exc.verdict)
    if not allowed:
        return SeedPage(url, False, None, None, "", False, False, "robots")

    try:
        response = request_with_backoff(client, url, retries=1, sleep=lambda _delay: None)
    except SsrfBlocked as exc:
        return SeedPage(url, False, None, None, "", False, True, exc.verdict)
    except ValueError as exc:
        return SeedPage(url, False, None, None, "", False, True, str(exc)[:200])
    except httpx.HTTPError as exc:
        return SeedPage(url, False, None, None, "", False, True, type(exc).__name__)

    final_url = str(response.url)
    html = response.text or ""
    status = response.status_code
    if not robots.is_allowed(final_url):
        return SeedPage(url, False, status, final_url, "", False, False, "robots")
    if is_aws_waf_challenge(status, html) or is_bot_challenge(html):
        return SeedPage(url, False, status, final_url, "", False, True, "bot_challenge")
    rendered = False
    if renderer is not None and 200 <= status < 400 and looks_like_js_shell(html):
        try:
            html = renderer.render(final_url)
            rendered = True
        except Exception as exc:
            return SeedPage(url, 200 <= status < 400, status, final_url, response.text or "", False, True, f"render:{type(exc).__name__}")
        if is_bot_challenge(html):
            return SeedPage(url, False, status, final_url, "", True, True, "bot_challenge")
    ok = 200 <= status < 400
    if not ok:
        html = ""
    return SeedPage(url, ok, status, final_url, html, rendered, True, None)
