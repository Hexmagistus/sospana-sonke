"""Page rendering for JavaScript-heavy careers pages (blueprint section 13).

A headless browser executes the page's JavaScript so job data injected at runtime
(e.g. JSON-LD added after load, or client-rendered listings) becomes visible. Kept
behind an interface so tests can inject a MockRenderer and run offline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings


class PageRenderer(ABC):
    @abstractmethod
    def render(self, url: str) -> str: ...


class PlaywrightRenderer(PageRenderer):
    def render(self, url: str) -> str:
        from playwright.sync_api import sync_playwright  # lazy import
        with sync_playwright() as p:
            kwargs = {}
            if settings.PLAYWRIGHT_EXECUTABLE_PATH:
                kwargs["executable_path"] = settings.PLAYWRIGHT_EXECUTABLE_PATH
            browser = p.chromium.launch(**kwargs)
            try:
                page = browser.new_page(user_agent=settings.PLAYWRIGHT_USER_AGENT)
                page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT_MS, wait_until="networkidle")
                return page.content()
            finally:
                browser.close()


class MockRenderer(PageRenderer):
    def __init__(self, html: str) -> None:
        self._html = html

    def render(self, url: str) -> str:
        return self._html
