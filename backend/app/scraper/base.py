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
from urllib.parse import parse_qs, urlparse

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
    # Match the registrable host, not a substring. "unilever.com" contains
    # the letters "lever.co" and must not be treated as a Lever board.
    if host == "lever.co" or host.endswith(".lever.co"):
        api_base = "https://api.eu.lever.co" if host.endswith(".eu.lever.co") else "https://api.lever.co"
        return "lever", {"token": _token_from_path(url), "api_base": api_base}
    if "smartrecruiters.com" in host:
        # careers.smartrecruiters.com/{Company} or {Company}.smartrecruiters.com.
        # A later path segment such as /south-africa is a country filter the
        # public API understands as country=za. Without it the global board
        # (thousands of jobs) is what comes back.
        token = _token_from_path(url)
        # jobs.smartrecruiters.com/{Company} puts the company in the path.
        # The "jobs" subdomain is not a company token.
        if host.endswith("smartrecruiters.com") and host not in (
                "careers.smartrecruiters.com", "www.smartrecruiters.com",
                "api.smartrecruiters.com", "jobs.smartrecruiters.com"):
            token = host.split(".")[0]
        config = {"token": token}
        for part in urlparse(url).path.strip("/").split("/"):
            iso = _SR_COUNTRY.get(part.lower())
            if iso:
                config["country"] = iso
                break
        return "smartrecruiters", config
    if "recruitee.com" in host:
        # {subdomain}.recruitee.com -- the subdomain is also the API token.
        token = host.split(".")[0] if host not in ("recruitee.com", "www.recruitee.com") else None
        return "recruitee", {"token": token}
    if "workable.com" in host:
        # apply.workable.com/{account}/... or, less commonly, {account}.workable.com
        token = _token_from_path(url)
        if host.endswith("workable.com") and host not in (
                "apply.workable.com", "www.workable.com", "workable.com"):
            token = host.split(".")[0]
        return "workable", {"token": token}
    workday = _detect_workday(host, url)
    if workday is not None:
        return workday
    oracle = _detect_oracle(host, url)
    if oracle is not None:
        return oracle
    if host.endswith(".breezy.hr"):
        return "breezy", {"token": host.split(".")[0]}
    if host.endswith(".pinpointhq.com"):
        return "pinpoint", {"host": host}
    # CareerInHR boards. The host is the tenant (atns.ci.hr). A substring
    # inside an unrelated name must not match.
    if host == "ci.hr" or host.endswith(".ci.hr"):
        return "cihr", {"host": host}
    # Still need a browser: SuccessFactors, Taleo, Jobvite, generic Workday
    # hosts that aren't the public candidate site. Render's free plan cannot
    # run Chromium, so these stay empty unless JS_RENDER_ENABLED is on.
    if any(h in host for h in ("successfactors", "taleo.net", "jobs.jobvite.com", "myworkday")):
        return "js", {}
    return "static", {}


# Path slugs on careers.smartrecruiters.com that the public API can filter.
_SR_COUNTRY = {"south-africa": "za"}


def _workday_facets(url: str) -> dict:
    """Country facet the career site already put on the URL. Sending it keeps
    a Malawi board from importing the employer's whole global list."""
    values = parse_qs(urlparse(url).query).get("locationCountry") or []
    return {"locationCountry": values} if values else {}


def _detect_workday(host: str, url: str) -> tuple[str, dict] | None:
    """Public Workday CXS boards: {tenant}.wdN.myworkdayjobs.com/{site}."""
    path = [p for p in urlparse(url).path.split("/") if p and not re.fullmatch(r"[a-z]{2}-[A-Za-z]{2}", p)]
    facets = _workday_facets(url)
    if host.endswith(".myworkdayjobs.com"):
        tenant = host.split(".")[0]
        site = path[0] if path else None
        if tenant and site:
            config = {"tenant": tenant, "site": site, "host": host}
            if facets:
                config["facets"] = facets
            return "workday", config
    if "myworkdaysite.com" in host and len(path) >= 3 and path[0] == "recruiting":
        config = {"tenant": path[1], "site": path[2], "host": host}
        if facets:
            config["facets"] = facets
        return "workday", config
    return None


def _detect_oracle(host: str, url: str) -> tuple[str, dict] | None:
    """Oracle Recruiting Cloud candidate sites. The public requisition API
    is what the career site itself calls; siteNumber CX is the default board
    on a dedicated host, CX_N when the path names one."""
    if "oraclecloud.com" not in host or "CandidateExperience" not in url:
        return None
    match = re.search(r"/sites/([^/?#]+)", url)
    site_name = match.group(1) if match else None
    if site_name and re.fullmatch(r"CX_\d+", site_name):
        site_number = site_name
    else:
        site_number = "CX"
    return "oracle", {"host": host, "site_number": site_number, "site_name": site_name}


def get_strategy(ats_type: str) -> ScrapeStrategy:
    from app.scraper.greenhouse import GreenhouseStrategy
    from app.scraper.lever import LeverStrategy
    from app.scraper.smartrecruiters import SmartRecruitersStrategy
    from app.scraper.recruitee import RecruiteeStrategy
    from app.scraper.workable import WorkableStrategy
    from app.scraper.workday import WorkdayStrategy
    from app.scraper.oracle_ce import OracleCEStrategy
    from app.scraper.breezy import BreezyStrategy
    from app.scraper.pinpoint import PinpointStrategy
    from app.scraper.cihr import CihrStrategy
    from app.scraper.static_html import StaticHTMLStrategy
    from app.scraper.rendered_html import RenderedHTMLStrategy
    return {
        "greenhouse": GreenhouseStrategy(),
        "lever": LeverStrategy(),
        "smartrecruiters": SmartRecruitersStrategy(),
        "recruitee": RecruiteeStrategy(),
        "workable": WorkableStrategy(),
        "workday": WorkdayStrategy(),
        "oracle": OracleCEStrategy(),
        "breezy": BreezyStrategy(),
        "pinpoint": PinpointStrategy(),
        "cihr": CihrStrategy(),
        "static": StaticHTMLStrategy(),
        "js": RenderedHTMLStrategy(),
    }.get(ats_type, StaticHTMLStrategy())


_TAG_RE = re.compile(r"<[^>]+>")
# Block-level boundaries that should become line breaks so structure survives.
_BLOCK_BREAK_RE = re.compile(r"</?(?:li|p|div|br|h[1-6]|ul|ol|tr)\b[^>]*>", re.IGNORECASE)
# Drop the element and its contents. A leftover <script> would otherwise
# become readable text, and the stored description is shown to candidates.
_UNTRUSTED_BLOCK_RE = re.compile(
    r"<(script|style|iframe|object|embed|noscript)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_EVENT_HANDLER_RE = re.compile(r"""\s+on[a-z]+\s*=\s*(['"]).*?\1""", re.IGNORECASE | re.DOTALL)
_JS_URL_RE = re.compile(r"""(?i)\b(?:javascript|data)\s*:""")


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    text = _UNTRUSTED_BLOCK_RE.sub(" ", html)
    text = _EVENT_HANDLER_RE.sub(" ", text)
    text = _JS_URL_RE.sub("", text)
    # Turn block boundaries into newlines first, then strip remaining inline tags.
    text = _BLOCK_BREAK_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"'))
    # Collapse spaces/tabs but preserve single newlines between lines.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()
