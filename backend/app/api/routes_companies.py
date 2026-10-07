"""Company database + URL-tester routes (blueprint Steps 4 & the URL tester).

Listing is available to any authenticated user; import, edit, and URL testing are
administrator-only (role-based access control).
"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, RedirectResponse
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
from app.services.category_groups import CATEGORY_GROUPS, canonical_type, stored_values_for, types_for_group
from app.services.country_names import canonical_country, is_country, spellings_for
from app.services import icon_cache
from app.services.csv_import import import_companies_from_csv
from app.services.link_report_service import create_link_report
from app.services.url_tester import test_url, status_from_result
from app.services.vacancy_counts import (
    companies_with_known_vacancy_count, country_vacancy_rollup, open_vacancy_counts,
)
from app.services.watch_service import trending_company_ids

_NEEDS_ATTENTION = {"needs_real_url", "needs_review", "no_url", "error"}

router = APIRouter(prefix="/companies", tags=["companies"])

# Columns the list/card payload never returns. Deferring them keeps description-sized
# text (notes stay — the card can show them) and the favicon/hash blobs off the wire
# from Postgres. A later attribute access would lazy-load; CompanyResponse does not.
_LIST_DEFER = (
    defer(Company.last_final_url),
    defer(Company.favicon_url),
    defer(Company.favicon_checked_at),
    defer(Company.favicon_data),
    defer(Company.favicon_mime),
    defer(Company.content_hash),
    defer(Company.content_checked_at),
    defer(Company.sector),
)

def _with_open_counts(db: Session, companies: list[Company]) -> list[CompanyResponse]:
    """Attach the real open-vacancy count. Two grouped queries for the page."""
    ids = [c.id for c in companies]
    counts = open_vacancy_counts(db, ids)
    known = companies_with_known_vacancy_count(db, ids)
    have_icons: dict[str, int] = {}
    if ids:
        have_icons = {
            cid: icon_cache.icon_version(checked)
            for cid, checked in db.query(Company.id, Company.favicon_checked_at).filter(
                Company.id.in_(ids),
                or_(
                    and_(Company.favicon_url.isnot(None), Company.favicon_url != ""),
                    Company.favicon_data.isnot(None),
                ),
            )
        }
    out: list[CompanyResponse] = []
    for company in companies:
        row = CompanyResponse.model_validate(company)
        n = counts.get(company.id, 0)
        row.open_vacancies = n
        row.open_vacancies_known = n > 0 or company.id in known
        row.has_icon = company.id in have_icons
        row.icon_version = have_icons.get(company.id)
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
    group: str | None = Query(default=None, max_length=20,
                              description="Explorer page group: universities, colleges, hospitals, ngos, government"),
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
        # The code plus its aliases (category_groups.ALIASES), e.g. SOE also finds PARASTATAL.
        query = query.filter(func.upper(Company.source_type).in_(stored_values_for(source_type)))
    if group:
        group_types = types_for_group(group)
        if group_types is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Unknown group. Use one of: {', '.join(CATEGORY_GROUPS)}.")
        query = query.filter(func.upper(Company.source_type).in_(group_types))
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
        scoped = bool(source_type or group or country or (q and q.strip()) or ids)
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
    invalidate_directory_stats_cache()


# Public landing-page counts. Cached in-process for 5 minutes (off under ENV=test),
# and the response carries Cache-Control: public, max-age=300 for the browser/CDN.
_STATS_TTL_SECONDS = 300.0
_stats_cache: dict = {"at": 0.0, "data": None}


def invalidate_directory_stats_cache() -> None:
    _stats_cache["data"] = None
    _stats_cache["at"] = 0.0


def _country_counts(db: Session, *conditions) -> dict[str, int]:
    rows = (db.query(Company.country, func.count(Company.id))
            .filter(Company.deleted_at.is_(None), Company.country.isnot(None),
                    Company.country != "", *conditions)
            .group_by(Company.country).all())
    out: dict[str, int] = {}
    for country, n in rows:
        name = canonical_country(country)
        if not name:
            continue
        out[name] = out.get(name, 0) + int(n)
    return out


@router.get("/stats")
@limiter.limit("60/minute")
def directory_stats(request: Request, response: Response, db: Session = Depends(get_db)):
    """Public counts only: employers and countries. No personal data.

    ``employers`` / ``by_country`` count every non-deleted directory row (the
    same population as the country tabs), including rows still waiting for a
    verified careers link.

    ``with_link`` / ``by_country_with_link`` count only employers that are
    ``active`` AND have a careers URL: the ones the landing page can honestly
    describe as "a direct link to their own careers page". The homepage prefers
    these and falls back to its built-in snapshot if the API is asleep.
    Country names use one homepage spelling. International and Africa stay in
    the maps (they are real rows) and are left out of ``countries``.
    """
    now = time.monotonic()
    cached = _stats_cache["data"]
    if settings.ENV != "test" and cached is not None and now - _stats_cache["at"] < _STATS_TTL_SECONDS:
        response.headers["Cache-Control"] = "public, max-age=300"
        return cached

    employers = db.query(func.count(Company.id)).filter(Company.deleted_at.is_(None)).scalar() or 0
    by_country = _country_counts(db)
    linked = (Company.active.is_(True), Company.careers_url.isnot(None), Company.careers_url != "")
    by_country_with_link = _country_counts(db, *linked)
    countries = sum(1 for name in by_country if is_country(name))
    payload = {
        "employers": int(employers),
        "countries": countries,
        "by_country": by_country,
        "with_link": int(sum(by_country_with_link.values())),
        "countries_with_link": sum(1 for name in by_country_with_link if is_country(name)),
        "by_country_with_link": by_country_with_link,
    }
    if settings.ENV != "test":
        _stats_cache["at"] = now
        _stats_cache["data"] = payload
    response.headers["Cache-Control"] = "public, max-age=300"
    return payload


@router.get("/facets")
def company_facets(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Counts for the directory's country tabs and headline stats -- numbers
    only, no company rows -- so the page never needs the full list."""
    now = time.monotonic()
    cached = _facets_cache["data"]
    if settings.ENV != "test" and cached is not None and now - _facets_cache["at"] < _FACETS_TTL_SECONDS:
        return cached
    rows = (db.query(Company.country, Company.source_type,
                     func.count(Company.id),
                     func.count(case((func.length(func.coalesce(Company.careers_url, "")) > 0, 1))))
            .filter(Company.deleted_at.is_(None))
            .group_by(Company.country, Company.source_type).all())
    country_counts: dict[str, int] = {}
    country_with_links: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    # The category chips must show what the list shows once a country is
    # chosen, so the type counts are also kept per country (canonical spelling,
    # same population as GET /companies?country=&source_type=).
    country_type_counts: dict[str, dict[str, int]] = {}
    country_type_with_links: dict[str, dict[str, int]] = {}
    total = with_links = 0
    for country, st, n, n_links in rows:
        # Aliases count under their canonical code, as GET /companies?source_type= lists them.
        key = canonical_type(st)
        if country:
            name = canonical_country(country)
            country_counts[name] = country_counts.get(name, 0) + n
            country_with_links[name] = country_with_links.get(name, 0) + n_links
            by_type = country_type_counts.setdefault(name, {})
            by_type[key] = by_type.get(key, 0) + n
            by_type_links = country_type_with_links.setdefault(name, {})
            by_type_links[key] = by_type_links.get(key, 0) + n_links
        type_counts[key] = type_counts.get(key, 0) + n
        total += n
        with_links += n_links
    # Per country: employers with a counted vacancy result ("Not counted yet"
    # is everyone else) and open vacancy rows held. Real rows only.
    country_counted: dict[str, int] = {}
    country_open_vacancies: dict[str, int] = {}
    for raw, (n_counted, n_open) in country_vacancy_rollup(db).items():
        name = canonical_country(raw)
        if not name:
            continue
        country_counted[name] = country_counted.get(name, 0) + n_counted
        country_open_vacancies[name] = country_open_vacancies.get(name, 0) + n_open
    payload = {"total": total, "with_links": with_links, "country_counts": country_counts,
               "country_with_links": country_with_links, "type_counts": type_counts,
               "country_type_counts": country_type_counts,
               "country_type_with_links": country_type_with_links,
               "country_counted": country_counted,
               "country_open_vacancies": country_open_vacancies}
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


_ICON_404_CACHE = "public, max-age=3600"
_ICON_NONE_CACHE = "public, max-age=86400"
_ICON_REDIRECT_CACHE = "public, max-age=86400"
_ICON_REDIRECT_VERSIONED_CACHE = "public, max-age=604800"
_ICON_BYTES_CACHE = "public, max-age=604800, stale-while-revalidate=86400"
# Only when the URL carries the current ?v= (see CompanyResponse.icon_version):
# a new icon gets a new URL, so this exact URL can never change.
_ICON_BYTES_IMMUTABLE = "public, max-age=31536000, immutable"


def _icon_response(request: Request, facts, icon, want: int | None) -> Response:
    """Build the icon reply. Every outcome, including "not found", is cacheable,
    so a browser or CDN asks again at most once per lifetime, not once per visit."""
    if facts is None:
        return JSONResponse({"detail": "Company not found."}, status_code=status.HTTP_404_NOT_FOUND,
                            headers={"Cache-Control": _ICON_404_CACHE})
    versioned = want is not None and want == facts.version
    if icon is not None:
        headers = {
            "Cache-Control": _ICON_BYTES_IMMUTABLE if versioned else _ICON_BYTES_CACHE,
            "ETag": icon.etag,
            "X-Content-Type-Options": "nosniff",
        }
        inm = request.headers.get("if-none-match")
        if inm and (inm.strip() == "*" or icon.etag in [p.strip().removeprefix("W/") for p in inm.split(",")]):
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
        return Response(content=icon.data, media_type=icon.mime, headers=headers)
    if facts.url:
        redirect = RedirectResponse(facts.url, status_code=status.HTTP_302_FOUND)
        redirect.headers["Cache-Control"] = (_ICON_REDIRECT_VERSIONED_CACHE if versioned
                                             else _ICON_REDIRECT_CACHE)
        return redirect
    # A known company with no icon. 204 (not 404) and cached for a day: a
    # directory of cards used to refetch every miss on each visit.
    return Response(status_code=status.HTTP_204_NO_CONTENT,
                    headers={"Cache-Control": _ICON_NONE_CACHE})


def _resolve_icon(company_id: str, session_factory, want: int | None):
    facts = icon_cache.facts_for(company_id, session_factory, want)
    icon = None
    if facts is not None and facts.has_data:
        icon = icon_cache.bytes_for(company_id, facts, session_factory)
    return facts, icon


@router.get("/{company_id}/icon")
async def company_icon(request: Request, company_id: str,
                       v: str | None = Query(default=None, max_length=20)):
    """Serve the company's own icon from OUR storage.

    The icon is fetched once, politely, by the ``discover_company_icons`` job
    (robots.txt honoured, rate-limited, size-capped) and stored on the company
    row. A page view never makes a request to the company's website or any
    third party from here. Rows from before the job existed may still carry
    just a URL; those redirect until the job has stored their bytes.

    async on purpose: a cache hit (the normal case, see app/services/icon_cache.py)
    is answered on the event loop with no threadpool thread and no DB
    connection, so a page of 100+ cards finishes in milliseconds instead of
    queueing behind the 5+2 DB pool and filling uvicorn's concurrency limit.
    Only a miss goes to a thread, and at most 3 of those touch the DB at once.

    Intentionally unauthenticated: a plain <img src> can't send an Authorization
    header, and this only ever exposes a company's own already-public favicon.
    """
    want = icon_cache.parse_version(v)
    if len(company_id) > 64:
        return _icon_response(request, None, None, want)
    hit = icon_cache.cached_without_db(company_id, want)
    if hit is not None:
        return _icon_response(request, hit[0], hit[1], want)
    # Tests swap get_db for a per-test database; honour that here too.
    dependency = request.app.dependency_overrides.get(get_db, get_db)
    factory = lambda: icon_cache.session_from_dependency(dependency)  # noqa: E731
    facts, icon = await run_in_threadpool(_resolve_icon, company_id, factory, want)
    return _icon_response(request, facts, icon, want)


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
