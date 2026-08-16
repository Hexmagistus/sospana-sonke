"""Rendered-HTML strategy: render JS, then reuse the JSON-LD JobPosting parser."""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.scraper.base import ScrapeStrategy, RawVacancy
from app.scraper.render import PageRenderer
from app.scraper.static_html import StaticHTMLStrategy


class RenderedHTMLStrategy(ScrapeStrategy):
    ats_type = "js"

    def __init__(self, renderer: PageRenderer | None = None) -> None:
        self._renderer = renderer

    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        renderer = self._renderer
        if renderer is None:
            # Production path: gated by the global switch to protect small instances.
            if not settings.JS_RENDER_ENABLED:
                return []
            from app.scraper.render import PlaywrightRenderer
            renderer = PlaywrightRenderer()
        html = renderer.render(source.url)
        return StaticHTMLStrategy().parse_html(html, source_url=source.url)
