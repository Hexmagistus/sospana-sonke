"""Hide listings that are not open opportunities, then hand them to the purge.

A row is removed from public pages when it is a news article, a blog post, or
a generic page; when it was posted more than 120 days ago and has no closing
date; when the title or body contains a past year from 2019 through last year;
when the title, or the file name or upload folder in its own link, names a
year from 2000 through last year; when the title or the file name names a day
that has passed, or a month that ended more than 30 days ago; or when its own
link answers HTTP 404 or 410.

The year-in-link and passed-date rules run in Python only. They are applied
when the scanner stores a row, by the daily quality pass, and by
``is_publicly_listed``; a stamped row is expired, so every SQL list hides it. The same rows are stamped
expired so the existing backup-then-delete job removes them.

The quality score starts at 100. A past year costs 80, a stale posting costs
70, and a non-opportunity or a dead link costs 100. Any of those reasons
hides the row. A thin but genuine advert keeps the completeness score the
scanner already stored.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import unquote, urlparse

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
# Titles and link file names are checked further back than descriptions, where
# old years are often law names ("Act 3 of 2000").
OLD_ADVERT_YEAR_START = 2000
PAST_MONTH_GRACE_DAYS = 30
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
    "manual_close": 100,
    "not_an_opportunity": 100,
    "past_date": 80,
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


_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))
_SEP = r"[\s\-_.,/]*"
_DAY_MONTH_YEAR = re.compile(
    rf"(?<![0-9])(\d{{1,2}})(?:st|nd|rd|th)?{_SEP}({_MONTH_RE})(?![a-z]){_SEP}(20\d\d)(?![0-9])",
    re.IGNORECASE,
)
_MONTH_YEAR = re.compile(rf"(?<![a-z])({_MONTH_RE})(?![a-z]){_SEP}(20\d\d)(?![0-9])", re.IGNORECASE)
_ISO_DATE = re.compile(r"(?<![0-9])(20\d\d)-(\d\d)-(\d\d)(?![0-9])")
# A year on its own: not part of a longer number, not an ISO standard edition
# ("9001:2015"), not an Australian postcode ("NSW 2000").
_TITLE_YEAR = re.compile(r"(?<![0-9:])(?<!NSW )(?<!VIC )(?<!ACT )(20\d\d)(?![0-9])", re.IGNORECASE)
_FILE_YEAR = re.compile(r"(?<![0-9a-z])(20\d\d)(?![0-9])", re.IGNORECASE)
_UPLOAD_FOLDER = re.compile(r"/(20\d\d)[/-](0[1-9]|1[0-2])(?:/|$)")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_LINK_COLUMNS = ("application_url", "canonical_url")


def _is_old_year(year: int, today: date) -> bool:
    return OLD_ADVERT_YEAR_START <= year < today.year


def _title_has_old_year(title: str | None, today: date) -> bool:
    return any(_is_old_year(int(m.group(1)), today) for m in _TITLE_YEAR.finditer(title or ""))


def link_name_parts(url: str | None) -> tuple[str, str]:
    """(path, last segment with query) of a link, decoded, ids removed."""
    if not url:
        return "", ""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return "", ""
    path = _UUID.sub(" ", unquote(parsed.path or ""))
    query = _UUID.sub(" ", unquote(parsed.query or ""))
    segments = [seg for seg in path.split("/") if seg]
    last = segments[-1] if segments else ""
    return path, f"{last} {query}".strip()


def _link_has_old_year(url: str | None, today: date) -> bool:
    path, name = link_name_parts(url)
    if not path and not name:
        return False
    for match in _UPLOAD_FOLDER.finditer(path):
        if _is_old_year(int(match.group(1)), today):
            return True
    return any(_is_old_year(int(m.group(1)), today) for m in _FILE_YEAR.finditer(name))


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


_POSTED_LABEL = re.compile(
    r"(publish|posted|post date|posting date|created|updated|listed|date opened|opening date)", re.IGNORECASE,
)
_CLOSING_LABEL = re.compile(r"(clos|expir|deadline|apply by|due|until|before)", re.IGNORECASE)
# An advert date with no label is usually the day it went up. It only counts
# once it is this old; a labelled closing date counts the day after it.
UNLABELLED_DATE_GRACE_DAYS = 30


def _label_before(pattern, text: str, start: int) -> bool:
    return bool(pattern.search(text[max(0, start - 25):start]))


def named_dates(text: str | None) -> list[tuple[date, str]]:
    """Dates a text names, as (date, kind). kind is closing, day or month.

    A month is returned as its last day. Dates labelled as the publishing day
    are left out; the stale-posting rule covers those.
    """
    if not text:
        return []
    found: list[tuple[date, str]] = []
    spans = []
    day_matches = [(m, int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
                   for m in _DAY_MONTH_YEAR.finditer(text)]
    iso_matches = [(m, int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in _ISO_DATE.finditer(text)]
    for match, year, month, day in day_matches + iso_matches:
        spans.append(match.span())
        if _label_before(_POSTED_LABEL, text, match.start()):
            continue
        try:
            named = date(year, month, day)
        except ValueError:
            continue
        kind = "closing" if _label_before(_CLOSING_LABEL, text, match.start()) else "day"
        found.append((named, kind))
    for match in _MONTH_YEAR.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue
        if _label_before(_POSTED_LABEL, text, match.start()):
            continue
        found.append((_month_end(int(match.group(2)), _MONTHS[match.group(1).lower()]), "month"))
    return found


def dates_have_passed(dates: list[tuple[date, str]], today: date) -> bool:
    """True when the named dates show the advert is over.

    Any date from today on means the advert may still be open (it is usually
    the closing date), so nothing is flagged.
    """
    if not dates or any(named >= today for named, _kind in dates):
        return False
    for named, kind in dates:
        if kind == "closing":
            return True
        if kind == "day" and named < today - timedelta(days=UNLABELLED_DATE_GRACE_DAYS):
            return True
        if kind == "month" and named + timedelta(days=PAST_MONTH_GRACE_DAYS) < today:
            return True
    return False


def text_names_passed_date(text: str | None, today: date) -> bool:
    """True when one text names a closing day that has passed, or an old advert date."""
    return dates_have_passed(named_dates(text), today)


def _readable_name(name: str) -> str:
    return re.sub(r"[_\-+]+", " ", name)


def old_advert_reasons(
    title: str | None,
    urls: tuple[str | None, ...],
    today: date,
) -> list[str]:
    """past_year / past_date found in the title or the advert's own link name."""
    reasons: list[str] = []
    dates = named_dates(title)
    for url in urls:
        dates.extend(named_dates(_readable_name(link_name_parts(url)[1])))
    names_future_day = any(named >= today for named, _kind in dates)
    if _title_has_old_year(title, today) or (
        not names_future_day and any(_link_has_old_year(url, today) for url in urls)
    ):
        reasons.append("past_year")
    if dates_have_passed(dates, today):
        reasons.append("past_date")
    return reasons


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
    for reason in old_advert_reasons(title, (application_url, canonical_url), day):
        if reason not in reasons:
            reasons.append(reason)
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


def is_manually_closed(vacancy: Vacancy) -> bool:
    """An operator closed this row after checking it. A rescan must not reopen it."""
    return "manual_close" in list(vacancy.quality_flags or [])


def apply_listing_quality(vacancy: Vacancy, when: datetime | None = None, today: date | None = None) -> list[str]:
    """Stamp a scanned row. A removal reason expires it so the purge can delete it."""
    from app.services.opportunity_expiry import mark_expired, sa_today

    day = today or sa_today(when)
    reasons = removal_reasons_for(vacancy, day)
    if is_manually_closed(vacancy):
        reasons = ["manual_close", *[r for r in reasons if r != "manual_close"]]
    vacancy.quality_flags = reasons or None
    if not reasons:
        return []
    vacancy.quality_score = listing_quality_score(reasons)
    mark_expired(vacancy, when)
    return reasons


def _rows_with_old_advert_names(db: Session, day: date, skip: set, expired_status: str) -> list[Vacancy]:
    """Rows whose title or link names an old year or a passed date.

    These rules are not expressible in portable SQL, so the light columns are
    read in pages and checked in Python. Only the matching rows are loaded.
    """
    light = (
        db.query(Vacancy.id, Vacancy.title, Vacancy.application_url, Vacancy.canonical_url)
        .filter(
            Vacancy.deleted_at.is_(None),
            or_(Vacancy.status.is_(None), Vacancy.status != expired_status),
        )
        .yield_per(2000)
    )
    ids = [
        row.id for row in light
        if row.id not in skip and old_advert_reasons(row.title, (row.application_url, row.canonical_url), day)
    ]
    found: list[Vacancy] = []
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        found.extend(db.query(Vacancy).filter(Vacancy.id.in_(chunk)).all())
    return found


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
    seen = {vacancy.id for vacancy in rows}
    rows.extend(_rows_with_old_advert_names(db, day, seen, STATUS_EXPIRED))
    counts = {
        "not_an_opportunity": 0, "past_year": 0, "past_date": 0,
        "stale_posting": 0, "dead_link": 0, "hidden": 0,
    }
    for vacancy in rows:
        reasons = removal_reasons_for(vacancy, day)
        if not reasons:
            reasons = ["not_an_opportunity"]
        for reason in reasons:
            if reason in counts:
                counts[reason] += 1
        if is_manually_closed(vacancy) and "manual_close" not in reasons:
            reasons = ["manual_close", *reasons]
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
        "past_date": text["past_date"],
        "stale_posting": text["stale_posting"],
        "dead_link": text["dead_link"] + links["dead_link"],
        "hidden": text["hidden"] + links["dead_link"],
        "links_checked": links["checked"],
    }
    detail = (
        f"hidden={summary['hidden']} not_an_opportunity={summary['not_an_opportunity']} "
        f"past_year={summary['past_year']} past_date={summary['past_date']} stale_posting={summary['stale_posting']} "
        f"dead_link={summary['dead_link']} links_checked={summary['links_checked']}"
    )
    db.add(AdminAuditLog(admin_id=_SYSTEM_ACTOR, action="review_listing_quality", detail=detail[:500]))
    db.commit()
    return summary
