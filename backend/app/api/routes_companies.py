"""Company database + URL-tester routes (blueprint Steps 4 & the URL tester).

Listing is available to any authenticated user; import, edit, and URL testing are
administrator-only (role-based access control).
"""
import asyncio
import inspect
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, defer

from app.core.config import settings
from app.core.deps import get_current_user, require_admin
from app.core.http_cache import private_short_cache
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.company import Company
from app.models.link_report import LinkReport
from app.models.user import User
from app.schemas.company import (
    CompanyResponse, CompanyImportResult, UrlTestResult, AutomationPolicyRequest, CoverageRow,
    TrendingCompany,
)
from app.schemas.link_report import LinkReportCreateRequest, LinkReportResponse
from app.services.country_names import canonical_country, is_country, spellings_for
from app.services.csv_import import import_companies_from_csv
from app.services.link_report_service import create_link_report
from app.services.logo_service import discover_favicon
from app.services.url_tester import test_url, status_from_result
from app.services.vacancy_counts import companies_with_known_vacancy_count, open_vacancy_counts
from app.services.watch_service import trending_company_ids

_NEEDS_ATTENTION = {"needs_real_url", "needs_review", "no_url", "error"}

# How long a discovered (or "nothing found") icon result stays cached on the
# company row before we try that company's site again.
_FAVICON_RECHECK = timedelta(days=30)

router = APIRouter(prefix="/companies", tags=["companies"])

# Columns the list/card payload never returns. Deferring them keeps description-sized
# text (notes stay — the card can show them) and the favicon/hash blobs off the wire
# from Postgres. A later attribute access would lazy-load; CompanyResponse does not.
_LIST_DEFER = (
    defer(Company.last_final_url),
    defer(Company.favicon_url),
    defer(Company.favicon_checked_at),
    defer(Company.content_hash),
    defer(Company.content_checked_at),
    defer(Company.sector),
)

# In-process icon cache on top of the 30-day DB cache. Repeat <img> loads on a
# directory page should not each open a DB round trip.
_ICON_CACHE_TTL = 600.0
_icon_cache: dict[str, tuple[float, str | None]] = {}


def _with_open_counts(db: Session, companies: list[Company]) -> list[CompanyResponse]:
    """Attach the real open-vacancy count. Two grouped queries for the page."""
    ids = [c.id for c in companies]
    counts = open_vacancy_counts(db, ids)
    known = companies_with_known_vacancy_count(db, ids)
    out: list[CompanyResponse] = []
    for company in companies:
        row = CompanyResponse.model_validate(company)
        n = counts.get(company.id, 0)
        row.open_vacancies = n
        row.open_vacancies_known = n > 0 or company.id in known
        out.append(row)
    return out


# Anti-bulk-copy: a regular user can't pull the whole directory in one call any
# more. Every non-admin request must be scoped (one country, one category, a
# search, or an explicit id list such as a shortlist) and is capped per call.
# The UI only ever shows one such slice at a time, so this costs it nothing.
_USER_MAX_ROWS = 1500
_UNSCOPED_USER_MAX_ROWS = 100


@router.get("", response_model=list[CompanyResponse])
@limiter.limit("200/hour", key_func=user_or_ip_key)
def list_companies(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    source_type: str | None = Query(default=None, max_length=20, description="Category, e.g. SOE, UNI, COLLEGE"),
    country: str | None = Query(default=None, max_length=80),
    q: str | None = Query(default=None, max_length=100, description="Search in name / JSE code"),
    ids: str | None = Query(default=None, max_length=8000, description="Comma-separated company ids"),
    active: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    private_short_cache(response)
    query = db.query(Company).options(*_LIST_DEFER).filter(Company.deleted_at.is_(None))
    if source_type:
        query = query.filter(Company.source_type == source_type.upper())
    if country:
        query = query.filter(Company.country.in_(spellings_for(country)))
    if q and q.strip():
        # Escape LIKE wildcards so user input is matched literally.
        raw = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        needle = f"%{raw}%"
        query = query.filter(or_(func.lower(Company.company_name).like(needle, escape="\\"),
                                 func.lower(func.coalesce(Company.jse_code, "")).like(needle, escape="\\")))
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()][:200]
        query = query.filter(Company.id.in_(id_list))
    if active is not None:
        query = query.filter(Company.active == active)
    if user.role != "admin":
        scoped = bool(source_type or country or (q and q.strip()) or ids)
        limit = min(limit, _USER_MAX_ROWS if scoped else _UNSCOPED_USER_MAX_ROWS)
    query = query.order_by(Company.company_name).offset(offset).limit(limit)
    return _with_open_counts(db, query.all())


# Directory headline counts change only when an admin imports or edits a row.
# A short in-process cache keeps the country tabs from re-running the group-by
# on every page load. Off under ENV=test so a test that inserts a row and then
# reads /facets cannot see a stale snapshot from an earlier test.
_FACETS_TTL_SECONDS = 60.0
_facets_cache: dict = {"at": 0.0, "data": None}


def invalidate_company_facets_cache() -> None:
    _facets_cache["data"] = None
    _facets_cache["at"] = 0.0


@router.get("/stats")
@limiter.limit("60/minute")
def directory_stats(request: Request, response: Response, db: Session = Depends(get_db)):
    """Public counts only: employers and countries. No personal data.

    Counts are non-deleted directory rows, the same population as the country
    tabs. The homepage uses these and falls back to the published seed totals
    if the API is asleep. by_country is the per-country split of that total,
    with one homepage spelling per country. International and Africa stay in
    by_country and in the employer total, and are left out of countries.
    """
    listed = Company.deleted_at.is_(None)
    employers = db.query(func.count(Company.id)).filter(listed).scalar() or 0
    rows = (db.query(Company.country, func.count(Company.id))
            .filter(listed, Company.country.isnot(None), Company.country != "")
            .group_by(Company.country).all())
    by_country: dict[str, int] = {}
    for country, n in rows:
        name = canonical_country(country)
        if not name:
            continue
        by_country[name] = by_country.get(name, 0) + int(n)
    # International and Africa stay in by_country (they are real rows) but
    # are not countries, so they do not inflate the country count.
    countries = sum(1 for name in by_country if is_country(name))
    response.headers["Cache-Control"] = "public, max-age=300"
    return {"employers": int(employers), "countries": countries, "by_country": by_country}


@router.get("/facets")
def company_facets(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Counts for the directory's country tabs and headline stats -- numbers
    only, no company rows -- so the page never needs the full list."""
    now = time.monotonic()
    cached = _facets_cache["data"]
    if settings.ENV != "test" and cached is not None and now - _facets_cache["at"] < _FACETS_TTL_SECONDS:
        return cached
    rows = (db.query(Company.country, Company.source_type,
                     func.count(Company.id), func.count(Company.careers_url))
            .filter(Company.deleted_at.is_(None))
            .group_by(Company.country, Company.source_type).all())
    country_counts: dict[str, int] = {}
    country_with_links: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    total = with_links = 0
    for country, st, n, n_links in rows:
        if country:
            name = canonical_country(country)
            country_counts[name] = country_counts.get(name, 0) + n
            country_with_links[name] = country_with_links.get(name, 0) + n_links
        key = (st or "").upper()
        type_counts[key] = type_counts.get(key, 0) + n
        total += n
        with_links += n_links
    payload = {"total": total, "with_links": with_links, "country_counts": country_counts,
               "country_with_links": country_with_links, "type_counts": type_counts}
    if settings.ENV != "test":
        _facets_cache["at"] = now
        _facets_cache["data"] = payload
    return payload


@router.get("/surprise", response_model=CompanyResponse)
@limiter.limit("60/hour", key_func=user_or_ip_key)
def surprise_company(request: Request, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """One random employer with a careers link (the directory's "Surprise me")."""
    c = (db.query(Company).options(*_LIST_DEFER)
         .filter(Company.deleted_at.is_(None), Company.careers_url.isnot(None),
                 Company.careers_url != "")
         .order_by(func.random()).first())
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No employers yet.")
    return _with_open_counts(db, [c])[0]


@router.get("/coverage", response_model=list[CoverageRow])
def coverage_map(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Honest per-country/category rollup: how much of the directory is a
    verified working link vs. still pending verification vs. needs attention.
    Doubles as the team's own to-do list for filling gaps, not just a stat for
    users -- see the "Full-Africa university coverage" note in the project
    doc for why this matters for the rows added fastest (universities)."""
    # Same buckets as the previous row-by-row pass, computed in SQL so a
    # multi-thousand-row directory is not loaded into Python on every view.
    country_expr = func.coalesce(func.nullif(Company.country, ""), "Unknown")
    type_expr = func.upper(func.coalesce(func.nullif(Company.source_type, ""), "OTHER"))
    has_url = and_(Company.careers_url.isnot(None), Company.careers_url != "")
    counted = (
        db.query(
            country_expr,
            type_expr,
            func.count(Company.id),
            func.sum(case((Company.active.is_(True), 1), else_=0)),
            func.sum(case((has_url, 1), else_=0)),
            func.sum(case((Company.scraping_status == "ok", 1), else_=0)),
            func.sum(case((Company.scraping_status == "pending", 1), else_=0)),
            func.sum(case((Company.scraping_status.in_(tuple(_NEEDS_ATTENTION)), 1), else_=0)),
        )
        .filter(Company.deleted_at.is_(None))
        .group_by(country_expr, type_expr)
        .order_by(country_expr, type_expr)
        .all()
    )
    merged: dict[tuple[str, str], list[int]] = {}
    for country, source_type, total, active, with_url, verified, pending, needs in counted:
        key = (canonical_country(country) or country, source_type)
        slot = merged.setdefault(key, [0, 0, 0, 0, 0, 0])
        for i, val in enumerate((total, active, with_url, verified, pending, needs)):
            slot[i] += int(val or 0)
    return [
        CoverageRow(
            country=country,
            source_type=source_type,
            total=vals[0],
            active=vals[1],
            with_careers_url=vals[2],
            verified_ok=vals[3],
            pending_verification=vals[4],
            needs_attention=vals[5],
        )
        for (country, source_type), vals in merged.items()
    ]


@router.get("/trending", response_model=list[TrendingCompany])
def trending_companies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, le=200),
):
    """Companies picking up the most notify-me subscriptions lately -- powers
    the directory's 🔥 "Popular this week" badge. See trending_company_ids()
    for why this (and not shares, which aren't tracked) is the signal used."""
    rows = trending_company_ids(db, days=days, limit=limit)
    return [TrendingCompany(company_id=cid, watch_count=cnt) for cid, cnt in rows]


@router.post("/{company_id}/report-link", response_model=LinkReportResponse,
            status_code=status.HTTP_201_CREATED)
def report_broken_link(company_id: str, body: LinkReportCreateRequest,
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Crowd-sourced verification: let any signed-in candidate flag a link
    that's broken, wrong, or redirects elsewhere -- far faster at scale than
    waiting for the periodic re-check or an admin's manual URL test."""
    report = create_link_report(db, user_id=user.id, company_id=company_id, reason=body.reason)
    return LinkReportResponse.model_validate(report)


@router.get("/link-reports", response_model=list[LinkReportResponse], dependencies=[Depends(require_admin)])
def list_link_reports(db: Session = Depends(get_db),
                      status_filter: str | None = Query(default=None, alias="status"),
                      limit: int = Query(default=100, le=500)):
    q = db.query(LinkReport)
    if status_filter:
        q = q.filter(LinkReport.status == status_filter)
    q = q.order_by(LinkReport.created_at.desc()).limit(limit)
    return [LinkReportResponse.model_validate(r) for r in q.all()]


def _icon_cached(company_id: str) -> tuple[bool, str | None]:
    hit = _icon_cache.get(company_id)
    if hit is None:
        return False, None
    at, url = hit
    if time.monotonic() - at > _ICON_CACHE_TTL:
        _icon_cache.pop(company_id, None)
        return False, None
    return True, url


def _discover_icon(website: str | None, careers_url: str | None) -> str | None:
    """Run favicon discovery off the event loop.

    discover_favicon is async (tests and the logo service use an async HTTP
    client). This route is a plain def so the blocking DB commit and the network
    wait run in FastAPI's threadpool instead of stalling every other request.
    An async test double is still awaited via asyncio.run inside that thread.
    """
    found = discover_favicon(website, careers_url)
    if inspect.isawaitable(found):
        return asyncio.run(found)
    return found


@router.get("/{company_id}/icon")
def company_icon(company_id: str, db: Session = Depends(get_db)):
    """Redirect to the real icon pulled directly from this company's own page —
    not a guessed domain. Cached on the company row (see Company.favicon_url) so
    a given company's site is fetched at most once every 30 days, and in this
    process for ten minutes so a page of cards does not re-query for each image.

    Intentionally unauthenticated: a plain <img src> can't send an Authorization
    header, and this only ever exposes a company's own already-public favicon —
    nothing about Sospana Sonke's data.
    """
    fresh, cached_url = _icon_cached(company_id)
    if fresh:
        if not cached_url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No icon found for this company.")
        redirect = RedirectResponse(cached_url, status_code=status.HTTP_302_FOUND)
        redirect.headers["Cache-Control"] = "public, max-age=86400"
        return redirect

    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    # SQLite (used in tests/dev) drops tzinfo from DateTime(timezone=True) columns
    # on read-back, so normalise before comparing rather than assuming Postgres's
    # behaviour everywhere.
    checked_at = company.favicon_checked_at
    if checked_at is not None and checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    stale = checked_at is None or datetime.now(timezone.utc) - checked_at > _FAVICON_RECHECK
    if stale:
        company.favicon_url = _discover_icon(company.official_website, company.careers_url)
        company.favicon_checked_at = datetime.now(timezone.utc)
        db.commit()

    _icon_cache[company.id] = (time.monotonic(), company.favicon_url)
    if not company.favicon_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No icon found for this company.")
    redirect = RedirectResponse(company.favicon_url, status_code=status.HTTP_302_FOUND)
    redirect.headers["Cache-Control"] = "public, max-age=86400"
    return redirect


_MAX_IMPORT_MB = 25  # admin-only, but still capped -- see app/api/routes_cv.py's
                     # _read_capped for why an unbounded await file.read() is unsafe.


@router.post("/import", response_model=CompanyImportResult, dependencies=[Depends(require_admin)])
async def import_companies(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a .csv file.")
    max_bytes = _MAX_IMPORT_MB * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail=f"File exceeds the {_MAX_IMPORT_MB} MB limit.")
        chunks.append(chunk)
    content = b"".join(chunks)
    result = import_companies_from_csv(db, content)
    invalidate_company_facets_cache()
    return result


@router.post("/{company_id}/test-url", response_model=UrlTestResult, dependencies=[Depends(require_admin)])
async def test_company_url(company_id: str, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    result = await test_url(company.careers_url)
    company.last_checked = datetime.now(timezone.utc)
    company.last_http_status = result.status_code
    company.last_final_url = result.final_url
    company.url_looks_like_careers = result.looks_like_careers
    company.scraping_status = status_from_result(result)
    db.commit()
    return result


@router.put("/{company_id}/automation-policy", response_model=CompanyResponse,
            dependencies=[Depends(require_admin)])
async def set_automation_policy(company_id: str, body: AutomationPolicyRequest,
                                db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    company.automation_mode = body.automation_mode
    company.requires_login = body.requires_login
    company.has_captcha = body.has_captcha
    db.commit()
    db.refresh(company)
    return _with_open_counts(db, [company])[0]
