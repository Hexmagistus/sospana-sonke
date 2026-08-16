"""Production Submitter using Playwright (headless Chromium).

Loads the page, fills the mapped fields, and submits. Import is lazy so the app
runs without Playwright installed when automation is disabled. Uses a configured
executable path (the browser bundled in the deploy image) when provided.
"""
from __future__ import annotations

from app.automation.base import Submitter, SubmissionResult
from app.core.config import settings


class PlaywrightSubmitter(Submitter):
    def __init__(self) -> None:
        from playwright.sync_api import sync_playwright  # lazy import
        self._sync_playwright = sync_playwright

    def _launch(self, p):
        kwargs = {}
        if settings.PLAYWRIGHT_EXECUTABLE_PATH:
            kwargs["executable_path"] = settings.PLAYWRIGHT_EXECUTABLE_PATH
        return p.chromium.launch(**kwargs)

    def load(self, url: str) -> str:
        with self._sync_playwright() as p:
            browser = self._launch(p)
            try:
                page = browser.new_page(user_agent=settings.PLAYWRIGHT_USER_AGENT)
                page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT_MS, wait_until="domcontentloaded")
                return page.content()
            finally:
                browser.close()

    def fill_and_submit(self, url: str, values: dict[str, str]) -> SubmissionResult:
        with self._sync_playwright() as p:
            browser = self._launch(p)
            try:
                page = browser.new_page(user_agent=settings.PLAYWRIGHT_USER_AGENT)
                page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT_MS, wait_until="domcontentloaded")
                for name, value in values.items():
                    locator = page.locator(f'[name="{name}"]')
                    if locator.count():
                        locator.first.fill(value)
                submit = page.locator('button[type="submit"], input[type="submit"]')
                if submit.count():
                    submit.first.click(timeout=settings.PLAYWRIGHT_TIMEOUT_MS)
                else:
                    page.keyboard.press("Enter")
                page.wait_for_load_state("networkidle", timeout=settings.PLAYWRIGHT_TIMEOUT_MS)
                return SubmissionResult("submitted", filled=dict(values))
            except Exception as exc:
                return SubmissionResult("failed", reason=f"{type(exc).__name__}: {exc}")
            finally:
                browser.close()
