"""Scraper strategy framework (blueprint section 13).

Different careers pages need different fetchers/parsers. Each source is tagged
with an ATS type, and a matching ScrapeStrategy is selected. Structured JSON feeds
(Greenhouse/Lever/SmartRecruiters) are strongly preferred over HTML scraping
because they are cheaper and more reliable; a static-HTML strategy is the fallback.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx


@dataclass
class RawVacancy:
    title: str
    external_id: str | None = None
    department: str | None = None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    salary: str | None = None
    posting_date: str | None = None      # ISO string; normalised later
    closing_date: str | None = None
    description: str | None = None
    application_url: str | None = None
    source_url: str | None = None
    raw: dict = field(default_factory=dict)


class ScrapeStrategy(ABC):
    ats_type: str = "unknown"

    @abstractmethod
    def fetch(self, source, client: httpx.Client) -> list[RawVacancy]:
        """Fetch and parse vacancies for a VacancySource. Raises on HTTP/parse errors."""
        raise NotImplementedError


# ---- ATS detection ----------------------------------------------------------

def _token_from_path(url: str) -> str | None:
    path = urlparse(url).path.strip("/")
    return path.split("/")[0] if path else None


def detect_ats(url: str) -> tuple[str, dict]:
    """Return (ats_type, config) for a careers URL. config may hold a board token."""
    host = (urlparse(url).hostname or "").lower()
    if "greenhouse.io" in host:
        return "greenhouse", {"token": _token_from_path(url)}
    if "lever.co" in host:
        return "lever", {"token": _token_from_path(url)}
    if "smartrecruiters.com" in host:
        # careers.smartrecruiters.com/{Company} or {Company}.smartrecruiters.com
        token = _token_from_path(url)
        if host.endswith("smartrecruiters.com") and host not in ("careers.smartrecruiters.com", "www.smartrecruiters.com", "api.smartrecruiters.com"):
            token = host.split(".")[0]
        return "smartrecruiters", {"token": token}
    # JavaScript-rendered ATSs (need a headless browser to read).
    if any(h in host for h in ("myworkdayjobs.com", "workday", "successfactors",
                               "oraclecloud.com", "taleo.net", "jobs.jobvite.com")):
        return "js", {}
    return "static", {}


def get_strategy(ats_type: str) -> ScrapeStrategy:
    from app.scraper.greenhouse import GreenhouseStrategy
    from app.scraper.lever import LeverStrategy
    from app.scraper.smartrecruiters import SmartRecruitersStrategy
    from app.scraper.static_html import StaticHTMLStrategy
    from app.scraper.rendered_html import RenderedHTMLStrategy
    return {
        "greenhouse": GreenhouseStrategy(),
        "lever": LeverStrategy(),
        "smartrecruiters": SmartRecruitersStrategy(),
        "static": StaticHTMLStrategy(),
        "js": RenderedHTMLStrategy(),
    }.get(ats_type, StaticHTMLStrategy())


_TAG_RE = re.compile(r"<[^>]+>")
# Block-level boundaries that should become line breaks so structure survives.
_BLOCK_BREAK_RE = re.compile(r"</?(?:li|p|div|br|h[1-6]|ul|ol|tr)\b[^>]*>", re.IGNORECASE)


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    # Turn block boundaries into newlines first, then strip remaining inline tags.
    text = _BLOCK_BREAK_RE.sub("\n", html)
    text = _TAG_RE.sub(" ", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"'))
    # Collapse spaces/tabs but preserve single newlines between lines.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()
