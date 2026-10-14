"""Hide listings that are not open opportunities, then hand them to the purge.

A row is removed from public pages when it is a news article, a blog post, or
a generic page; when it was posted more than 120 days ago and has no closing
date; when the title or body contains a past year from 2019 through last year;
or when its own link answers HTTP 404 or 410. The same rows are stamped
expired so the existing backup-then-delete job removes them.

The quality score starts at 100. A past year costs 80, a stale posting costs
70, and a non-opportunity or a dead link costs 100. Any of those reasons
hides the row. A thin but genuine advert keeps the completeness score the
scanner already stored.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import and_, func, not_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.admin_ops import AdminAuditLog
from app.models.vacancy import Vacancy
from app.scraper.politeness import RateLimiter
from app.scraper.ssrf import SsrfBlocked, assert_safe_fetch_url

logger = logging.getLogger(__name__)

STALE_POSTING_DAYS = 120
PAST_YEAR_START = 2019
DEAD_LINK_STATUSES = (404, 410)
_SYSTEM_ACTOR = "00000000-0000-0000-0000-000000000000"

# Whole-title labels that are site pages, not a role.
GENERIC_TITLES = (
    "careers", "jobs", "job", "vacancies", "vacancy", "home", "homepage",
    "about", "about us", "contact", "contact us", "news", "blog", "press",
    "media", "welcome", "our story", "sitemap", "privacy policy",
    "cookie policy", "latest news", "newsroom", "press room",
)

_ROLE_KEEP = (
    "vacanc", "position", "internship", "learnership", "bursary", "recruit", "hiring",
)
_NEWS_TITLE_BITS = ("announces", "welcomes")
_NEWS_URL_BITS = (
    "%/news/%", "%/news-%", "%/blog/%", "%/blog-%", "%/stories/%", "%/articles/%",
    "%/press-release/%", "%/press-releases/%",
)
_URL_COLUMNS = ("application_url", "canonical_url", "source_url")

_SCORE_PENALTY = {
    "not_an_opportunity": 100,
    "dead_link": 100,
    "past_year": 80,
    "stale_posting": 70,
}


def past_years(today: date) -> list[int]:
    """2019 through the year before ``today``. The current year is not past."""
    last = today.year - 1
    if last < PAST_YEAR_START:
        return []
    return list(range(PAST_YEAR_START, last + 1))


def listing_quality_score(flags: list[str]) -> int:
    """100 when nothing is wrong. Each removal reason lowers the score."""
    score = 100
    for flag in dict.fromkeys(flags):
        score -= _SCORE_PENALTY.get(flag, 50)
    return max(0, score)


def _norm_title(title: str | None) -> str:
    text = " ".join((title or "").split()).strip().lower()
    return text.strip(" -|»>")


def _has_role_word(title: str | None) -> bool:
    text = _norm_title(title)
    return any(word in text for word in _ROLE_KEEP)


def _is_generic_title(title: str | None) -> bool:
    text = _norm_title(title)
    if not text:
        return False
    if text in GENERIC_TITLES:
        return True
    if text.endswith(" careers"):
        return True
    if text.startswith("careers -") or text.startswith("careers –"):
        return True
    if text.startswith("careers:") or text.startswith("careers |"):
        return True
    return False


def _is_news_title(title: str | None) -> bool:
    text = _norm_title(title)
    if not text or _has_role_word(title):
        return False
    return any(bit in text for bit in _NEWS_TITLE_BITS)


def _is_news_url(url: str | None, title: str | None) -> bool:
    if not url or _has_role_word(title):
        return False
    lowered = url.lower()
    needles = (
        "/news/", "/news-", "/blog/", "/blog-", "/stories/", "/articles/",
        "/press-release/", "/press-releases/",
    )
    return any(needle in lowered for needle in needles)


def _text_has_past_year(title: str | None, description: str | None, today: date) -> bool:
    blob = f"{title or ''}\n{description or ''}"
    return any(str(year) in blob for year in past_years(today))


def _is_stale_posting(posting: date | None, closing: date | None, today: date) -> bool:
    if posting is None or closing is not None:
        return False
    return posting < today - timedelta(days=STALE_POSTING_DAYS)


def removal_reasons(
    *,
    title: str | None,
    description: str | None,
    posting_date: date | None,
    closing_date: date | None,
    application_url: str | None = None,
    canonical_url: str | None = None,
    source_url: str | None = None,
    link_http_status: int | None = None,
    today: date | None = None,
) -> list[str]:
    """Why a listing must leave the public pages. Empty means it can stay."""
    if today is None:
        from app.services.opportunity_expiry import sa_today
        day = sa_today()
    else:
        day = today
    reasons: list[str] = []
    urls = (application_url, canonical_url, source_url)
    if (
        _is_generic_title(title)
        or _is_news_title(title)
        or any(_is_news_url(url, title) for url in urls)
    ):
        reasons.append("not_an_opportunity")
    if _text_has_past_year(title, description, day):
        reasons.append("past_year")
    if _is_stale_posting(posting_date, closing_date, day):
        reasons.append("stale_posting")
    if link_http_status in DEAD_LINK_STATUSES:
        reasons.append("dead_link")
    return reasons


def removal_reasons_for(vacancy: Vacancy, today: date | None = None) -> list[str]:
    return removal_reasons(
        title=vacancy.title,
        description=vacancy.description,
        posting_date=vacancy.posting_date,
        closing_date=vacancy.closing_date,
        application_url=vacancy.application_url,
        canonical_url=vacancy.canonical_url,
        source_url=vacancy.source_url,
        link_http_status=vacancy.link_http_status,
        today=today,
    )


def _role_keep_sql():
    return or_(*(Vacancy.title.ilike(f"%{word}%") for word in _ROLE_KEEP))


def _url_match(pattern: str):
    parts = []
    for name in _URL_COLUMNS:
        column = getattr(Vacancy, name)
        parts.append(and_(column.isnot(None), column.ilike(pattern)))
    return or_(*parts)


def quality_failure_clause(today: date):
    """SQL twin of :func:`removal_reasons`. True when the row must be hidden."""
    parts = []
    for year in past_years(today):
        token = str(year)
        parts.append(Vacancy.title.contains(token))
        parts.append(and_(Vacancy.description.isnot(None), Vacancy.description.contains(token)))
    lowered = func.lower(Vacancy.title)
    parts.append(or_(
        lowered.in_(GENERIC_TITLES),
        lowered.like("% careers"),
        lowered.like("careers -%"),
        lowered.like("careers –%"),
        lowered.like("careers:%"),
        lowered.like("careers |%"),
    ))
    parts.append(and_(
        or_(*(Vacancy.title.ilike(f"%{bit}%") for bit in _NEWS_TITLE_BITS)),
        not_(_role_keep_sql()),
    ))
    parts.append(and_(
        or_(*(_url_match(pattern) for pattern in _NEWS_URL_BITS)),
        not_(_role_keep_sql()),
    ))
    cutoff = today - timedelta(days=STALE_POSTING_DAYS)
    parts.append(and_(
        Vacancy.closing_date.is_(None),
        Vacancy.posting_date.isnot(None),
        Vacancy.posting_date < cutoff,
    ))
    parts.append(and_(
        Vacancy.link_http_status.isnot(None),
        Vacancy.link_http_status.in_(DEAD_LINK_STATUSES),
    ))
    return or_(*parts)


def apply_listing_quality(vacancy: Vacancy, when: datetime | None = None, today: date | None = None) -> list[str]:
    """Stamp a scanned row. A removal reason expires it so the purge can delete it."""
    from app.services.opportunity_expiry import mark_expired, sa_today

    day = today or sa_today(when)
    reasons = removal_reasons_for(vacancy, day)
    vacancy.quality_flags = reasons or None
    if not reasons:
        return []
    vacancy.quality_score = listing_quality_score(reasons)
    mark_expired(vacancy, when)
    return reasons


def stamp_text_failures(db: Session, today: date | None = None, when: datetime | None = None) -> dict:
    """Expire rows the text rules already hide. No network."""
    from app.services.opportunity_expiry import STATUS_EXPIRED, mark_expired, sa_today

    moment = when or datetime.now(timezone.utc)
    day = today or sa_today(moment)
    rows = (
        db.query(Vacancy)
        .filter(
            Vacancy.deleted_at.is_(None),
            or_(Vacancy.status.is_(None), Vacancy.status != STATUS_EXPIRED),
            quality_failure_clause(day),
        )
        .all()
    )
    counts = {"not_an_opportunity": 0, "past_year": 0, "stale_posting": 0, "dead_link": 0, "hidden": 0}
    for vacancy in rows:
        reasons = removal_reasons_for(vacancy, day)
        if not reasons:
            reasons = ["not_an_opportunity"]
        for reason in reasons:
            if reason in counts:
                counts[reason] += 1
        vacancy.quality_flags = reasons
        vacancy.quality_score = listing_quality_score(reasons)
        mark_expired(vacancy, moment)
        counts["hidden"] += 1
    if counts["hidden"]:
        db.commit()
    else:
        db.flush()
    return counts


def _listing_url(vacancy: Vacancy) -> str | None:
    for name in _URL_COLUMNS:
        value = getattr(vacancy, name)
        if value and str(value).strip():
            return str(value).strip()
    return None


def _fetch_status(url: str, client: httpx.Client) -> int | None:
    try:
        assert_safe_fetch_url(url)
    except SsrfBlocked:
        return None
    try:
        response = client.get(url)
    except Exception:
        logger.info("listing link check failed for host %s", urlparse(url).netloc)
        return None
    return int(response.status_code)


def check_dead_links(
    db: Session,
    *,
    client: httpx.Client | None = None,
    limit: int = 25,
    max_seconds: float = 40.0,
    when: datetime | None = None,
    sleep=time.sleep,
) -> dict:
    """Check listing URLs that have not been checked. 404 and 410 expire the row."""
    from app.services.opportunity_expiry import mark_expired

    if limit <= 0:
        return {"checked": 0, "dead_link": 0}
    moment = when or datetime.now(timezone.utc)
    rows = (
        db.query(Vacancy)
        .filter(
            Vacancy.deleted_at.is_(None),
            Vacancy.is_open.is_(True),
            Vacancy.link_checked_at.is_(None),
            or_(
                Vacancy.application_url.isnot(None),
                Vacancy.canonical_url.isnot(None),
                Vacancy.source_url.isnot(None),
            ),
        )
        .order_by(Vacancy.last_seen_at.asc())
        .limit(limit)
        .all()
    )
    owns_client = client is None
    if owns_client:
        client = httpx.Client(
            timeout=httpx.Timeout(5.0, connect=3.0),
            follow_redirects=True,
            headers={"User-Agent": settings.URL_TEST_USER_AGENT},
        )
    limiter = RateLimiter(min_interval_seconds=1.0)
    started = time.monotonic()
    checked = dead = 0
    seen: dict[str, int | None] = {}
    try:
        for vacancy in rows:
            if max_seconds - (time.monotonic() - started) < 1.0:
                break
            url = _listing_url(vacancy)
            if not url:
                continue
            if url not in seen:
                limiter.wait(url, sleep=sleep)
                seen[url] = _fetch_status(url, client)
            status_code = seen[url]
            vacancy.link_checked_at = moment
            if status_code is None:
                checked += 1
                continue
            vacancy.link_http_status = status_code
            checked += 1
            if status_code in DEAD_LINK_STATUSES:
                flags = list(vacancy.quality_flags or [])
                if "dead_link" not in flags:
                    flags.append("dead_link")
                vacancy.quality_flags = flags
                vacancy.quality_score = listing_quality_score(flags)
                mark_expired(vacancy, moment)
                dead += 1
        db.commit()
    finally:
        if owns_client and client is not None:
            client.close()
    return {"checked": checked, "dead_link": dead}


def review_listing_quality(
    db: Session,
    *,
    client: httpx.Client | None = None,
    link_limit: int = 25,
    max_seconds: float = 40.0,
    today: date | None = None,
    when: datetime | None = None,
    sleep=time.sleep,
) -> dict:
    """Stamp text failures, then check a batch of links. Writes an audit row."""
    text = stamp_text_failures(db, today=today, when=when)
    links = check_dead_links(
        db, client=client, limit=link_limit, max_seconds=max_seconds, when=when, sleep=sleep,
    )
    summary = {
        "not_an_opportunity": text["not_an_opportunity"],
        "past_year": text["past_year"],
        "stale_posting": text["stale_posting"],
        "dead_link": text["dead_link"] + links["dead_link"],
        "hidden": text["hidden"] + links["dead_link"],
        "links_checked": links["checked"],
    }
    detail = (
        f"hidden={summary['hidden']} not_an_opportunity={summary['not_an_opportunity']} "
        f"past_year={summary['past_year']} stale_posting={summary['stale_posting']} "
        f"dead_link={summary['dead_link']} links_checked={summary['links_checked']}"
    )
    db.add(AdminAuditLog(admin_id=_SYSTEM_ACTOR, action="review_listing_quality", detail=detail[:500]))
    db.commit()
    return summary
