"""Company icon discovery — fetches the REAL favicon/logo straight off a
company's own page, rather than guessing a domain (that guessing chain still
lives client-side in frontend/src/components/CompanyLogo.tsx as a fallback for
when this can't find anything). Mirrors app/services/url_tester.py's shape.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings

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
    except Exception:
        return None
    finally:
        if owns_client:
            await client.aclose()
    return None
