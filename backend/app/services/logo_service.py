"""Company icon discovery — fetches the REAL favicon/logo straight off a
company's own page, rather than guessing a domain. (The old client-side guessing
chain was retired from frontend/src/components/CompanyLogo.tsx: the browser no
longer asks third parties for logos; it shows the stored icon or a monogram.)
Mirrors app/services/url_tester.py's shape.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings
from app.scraper.politeness import RateLimiter, RobotsChecker
from app.scraper.ssrf import SsrfBlocked, assert_safe_fetch_url

logger = logging.getLogger(__name__)

# Careers links that sit on a third-party ATS / job board — their favicon is the
# platform's, not the employer's, so we never treat one of these as the source.
# Keep this in sync with frontend/src/components/CompanyLogo.tsx's ATS_DOMAINS.
_ATS_DOMAINS = [
    "myworkdayjobs.com", "workday.com", "myworkdaysite.com",
    "successfactors.com", "sapsf.com", "oraclecloud.com", "taleo.net",
    "greenhouse.io", "lever.co", "smartrecruiters.com", "workable.com",
    "erecruit.co", "erecruit.co.za", "mcidirecthire.com", "pnet.co.za", "careers24.com",
    "simplify.hr", "jobvite.com", "icims.com", "bamboohr.com", "breezy.hr",
    "recruitmentportal.co.za", "ci.hr", "placementpartner.co.za", "mnetjobs.com",
    "eightfold.ai", "pinpointhq.com", "csod.com", "trending-talent.com",
    "wamly.io", "hr.com", "jobartis.com", "emprego.co.mz",
    "vacancymail.co.zw", "jobwebzambia.com", "greatzambiajobs.com", "lesothoyp.com",
    "makeyourmove.co.tz", "myjob.mu", "jobsearchmalawi.com", "brightermonday.co.tz",
    "linkedin.com", "facebook.com", "indeed.com", "za.indeed.com", "blogspot.com",
    "scubedonline.co.za", "skillsmapafrica.com", "applicantpro.com",
    "myjobmag.co.za", "myjobmag.com", "builtin.com",
]

_ICON_LINK_RE = re.compile(
    r"<link\s+[^>]*rel=[\"'](?:shortcut icon|icon|apple-touch-icon(?:-precomposed)?)[\"'][^>]*>",
    re.IGNORECASE,
)
_HREF_RE = re.compile(r"href=[\"']([^\"']+)[\"']", re.IGNORECASE)


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.hostname.lower().removeprefix("www.") if parsed.hostname else None
    except Exception:
        return None


def _is_ats(domain: str | None) -> bool:
    return bool(domain) and any(domain == d or domain.endswith(f".{d}") for d in _ATS_DOMAINS)


def _pick_source_url(official_website: str | None, careers_url: str | None) -> str | None:
    """The real employer page to fetch an icon from — the official site if we
    have one, otherwise a careers URL as long as it isn't ATS-hosted."""
    if official_website:
        return official_website
    if careers_url and not _is_ats(_domain(careers_url)):
        return careers_url
    return None


async def discover_favicon(
    official_website: str | None,
    careers_url: str | None,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Fetch the company's own page and pull out its actual favicon/apple-touch-icon
    href, resolved to an absolute URL. Returns None if there's nothing usable to
    fetch, the fetch fails, or no icon link is found there.

    `client` is injectable (mirrors app/services/url_tester.test_url) so tests can
    supply an httpx.MockTransport instead of hitting the real network.
    """
    candidate = _pick_source_url(official_website, careers_url)
    if not candidate:
        return None
    url = candidate if "://" in candidate else f"https://{candidate}"

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            timeout=settings.URL_TEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": settings.URL_TEST_USER_AGENT},
        )
    try:
        resp = await client.get(url)
        if resp.status_code >= 400:
            return None
        base = str(resp.url)

        best_href, best_rank = None, -1
        for tag in _ICON_LINK_RE.findall(resp.text):
            href_match = _HREF_RE.search(tag)
            if not href_match:
                continue
            # Prefer apple-touch-icon: usually a real square brand mark,
            # where a bare favicon can be a tiny/blank 16x16 placeholder.
            rank = 2 if "apple-touch-icon" in tag.lower() else 1
            if rank > best_rank:
                best_rank, best_href = rank, href_match.group(1)
        if best_href:
            return urljoin(base, best_href)

        # No explicit <link> tag — try the conventional default location.
        fallback = urljoin(base, "/favicon.ico")
        head_resp = await client.head(fallback)
        if head_resp.status_code < 400:
            return fallback
    except Exception as exc:
        logger.debug("Favicon discovery failed for %s: %s", url, exc)
        return None
    finally:
        if owns_client:
            await client.aclose()
    return None


# ---------------------------------------------------------------------------
# Fetch-once, store-ourselves icon pipeline (used by the discover_company_icons
# job — never by a page view). Polite by construction: robots.txt is honoured,
# requests to one host are spaced out, the response size is capped, only a
# sniffed raster image is accepted (no SVG: it can carry script), and a miss is
# remembered so we do not keep asking.
# ---------------------------------------------------------------------------

MAX_ICON_BYTES = 96 * 1024
_MAX_PAGE_BYTES = 400 * 1024
_MAX_ICON_CANDIDATES = 3


@dataclass(frozen=True)
class FetchedIcon:
    source_url: str
    data: bytes
    mime: str


def sniff_image_mime(data: bytes) -> str | None:
    """Trust the bytes, not the header. Raster formats a browser <img> can show."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] == b"\x00\x00\x01\x00":
        return "image/x-icon"
    return None


def _read_capped(client: httpx.Client, url: str, limit: int) -> tuple[bytes, str] | None:
    """GET `url`, streaming, and give up if it is an error or larger than `limit`."""
    assert_safe_fetch_url(url)
    with client.stream("GET", url) as resp:
        if resp.status_code >= 400:
            return None
        # Redirects are followed by the client; make sure the landing host is public too.
        assert_safe_fetch_url(str(resp.url))
        declared = resp.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            return None
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_bytes():
            total += len(chunk)
            if total > limit:
                return None
            chunks.append(chunk)
        final_url = str(resp.url)
    return b"".join(chunks), final_url


def _ranked_icon_hrefs(html: str, base: str) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    for order, tag in enumerate(_ICON_LINK_RE.findall(html)):
        href = _HREF_RE.search(tag)
        if not href:
            continue
        absolute = urljoin(base, href.group(1))
        if urlparse(absolute).path.lower().endswith(".svg") or absolute.startswith("data:"):
            continue
        rank = 2 if "apple-touch-icon" in tag.lower() else 1
        ranked.append((-rank, order, absolute))
    ranked.sort()
    urls = [u for _, _, u in ranked]
    urls.append(urljoin(base, "/favicon.ico"))
    seen: set[str] = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def _try_icon(client: httpx.Client, robots: RobotsChecker, limiter: RateLimiter,
              icon_url: str) -> FetchedIcon | None:
    if not robots.is_allowed(icon_url):
        return None
    limiter.wait(icon_url)
    got = _read_capped(client, icon_url, MAX_ICON_BYTES)
    if got is None or not got[0]:
        return None
    data = got[0]
    mime = sniff_image_mime(data)
    return FetchedIcon(icon_url, data, mime) if mime else None


def fetch_company_icon(
    official_website: str | None,
    careers_url: str | None,
    client: httpx.Client,
    robots: RobotsChecker,
    limiter: RateLimiter,
    known_icon_url: str | None = None,
) -> FetchedIcon | None:
    """Fetch (and size/type-check) one company's own icon, politely.

    `known_icon_url` is an icon URL found by an earlier run: we try that first
    (one request) and only re-read the company's page when it no longer works.
    Returns None when there is nothing usable — callers store that fact and the
    UI shows the monogram badge.
    """
    try:
        if known_icon_url:
            found = _try_icon(client, robots, limiter, known_icon_url)
            if found:
                return found
        candidate = _pick_source_url(official_website, careers_url)
        if not candidate:
            return None
        page = candidate if "://" in candidate else f"https://{candidate}"
        if not robots.is_allowed(page):
            return None
        limiter.wait(page)
        got = _read_capped(client, page, _MAX_PAGE_BYTES)
        if got is None:
            return None
        html = got[0].decode("utf-8", errors="ignore")
        for icon_url in _ranked_icon_hrefs(html, got[1])[:_MAX_ICON_CANDIDATES]:
            found = _try_icon(client, robots, limiter, icon_url)
            if found:
                return found
    except SsrfBlocked as exc:
        logger.debug("Icon fetch refused for %s: %s", official_website or careers_url, exc)
    except Exception as exc:  # network, TLS, decode: a miss, never a crash
        logger.debug("Icon fetch failed for %s: %s", official_website or careers_url, exc)
    return None


def has_icon_source(official_website: str | None, careers_url: str | None,
                    known_icon_url: str | None = None) -> bool:
    """False when only the monogram can ever apply (no own site, ATS-only careers)."""
    return bool(known_icon_url or _pick_source_url(official_website, careers_url))
