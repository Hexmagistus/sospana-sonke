"""Vacancy discovery routes (blueprint Steps 5 & 21).

Scanning and source inspection are administrator-only. Vacancy listing/detail are
available to any authenticated user (candidates browse matched vacancies; the
matching module will layer per-candidate scoring on top in the next step).
"""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, defer

from app.core.deps import get_current_user, require_admin
from app.core.http_cache import private_short_cache
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.admin_ops import AdminAuditLog
from app.models.company import Company
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource
from app.models.vacancy_report import VacancyReport, VACANCY_REPORT_CATEGORIES
from app.schemas.vacancy import (
    VacancyResponse, VacancyDetailResponse, VacancySourceResponse, ScanReportResponse,
    VacancyReportCreate, VacancyReportResponse, DuplicateGroupResponse,
    ExternalIdDuplicateGroupResponse,
    MergeDuplicatesRequest, MergeDuplicatesResponse,
    PublicJobResponse, PublicJobListResponse, PublicJobDetailResponse, OpportunityCountResponse,
    JobFacetsResponse, JobFacetCount, JobSuggestResponse, JobIdListResponse,
    SavedOpportunityCreate, AdminVacancyListResponse, AdminVacancyRow,
)
from app.services.flagship import FLAGSHIP_COUNTRY, countries_flagship_first, flagship_role_rank
from app.services.opportunity_expiry import expired_role_clauses, is_publicly_listed, public_role_clauses
from app.services.opportunity_tombstone import public_id_was_deleted
from app.services.opportunity_type import OPPORTUNITY_TYPES
from app.services.search_terms import expand_title_terms, opportunity_types_for
from app.models.saved_opportunity import SavedOpportunity
import re
from app.services.scan_service import scan_company
from app.services.duplicate_service import find_duplicate_groups, find_external_id_groups, merge_duplicates
from app.services.vacancy_report_service import create_vacancy_report

router = APIRouter(tags=["vacancies"])

# List cards never return the advertisement body. Leaving these Text columns in
# the SELECT made every page pull the raw scrape into Python.
_LIST_DEFER = (
    defer(Vacancy.description), defer(Vacancy.raw_content),
    defer(Vacancy.requirements_text), defer(Vacancy.qualifications), defer(Vacancy.experience),
)


@router.post("/companies/{company_id}/scan", response_model=list[ScanReportResponse])
@limiter.limit("20/hour")
def trigger_scan(request: Request, company_id: str, db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    """Manually scan one company's careers source. Admin only, rate-limited, audit-logged.

    Runs in this request so the admin can read the result. It does not scan the
    whole directory. Ordinary candidates cannot call it.
    """
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    reports = scan_company(db, company)
    status_note = reports[0].status if reports else "none"
    db.add(AdminAuditLog(
        admin_id=admin.id, action="scan_now", target_user_id=None,
        detail=f"company={company_id} status={status_note}"[:500],
    ))
    db.commit()
    return [ScanReportResponse(**asdict(r)) for r in reports]


@router.get("/companies/{company_id}/sources", response_model=list[VacancySourceResponse],
            dependencies=[Depends(require_admin)])
def list_sources(company_id: str, db: Session = Depends(get_db)):
    rows = db.query(VacancySource).filter(VacancySource.company_id == company_id).all()
    return [VacancySourceResponse.model_validate(r) for r in rows]


@router.get("/companies/{company_id}/vacancies", response_model=list[VacancyResponse])
def list_company_vacancies(company_id: str, response: Response, db: Session = Depends(get_db),
                           user: User = Depends(get_current_user),
                           is_open: bool | None = Query(default=True)):
    private_short_cache(response)
    q = db.query(Vacancy).options(*_LIST_DEFER).filter(Vacancy.company_id == company_id)
    if user.role != "admin":
        q = q.filter(*public_role_clauses())
    elif is_open is False:
        q = q.filter(or_(Vacancy.status == "expired", Vacancy.is_open.is_(False)))
    elif is_open is not False:
        q = q.filter(*public_role_clauses())
    return [VacancyResponse.model_validate(v) for v in q.order_by(Vacancy.last_seen_at.desc()).all()]


def _like_fragment(term: str) -> str:
    """A bounded contains-match. Percent and underscore are not wildcards from the caller."""
    cleaned = term.strip()[:80].replace("\\", "").replace("%", "").replace("_", "")
    return f"%{cleaned}%"


def _apply_link(vacancy: Vacancy) -> str | None:
    return vacancy.application_url or vacancy.canonical_url or vacancy.source_url or None


def _public_job(vacancy: Vacancy, company: Company) -> PublicJobResponse:
    return PublicJobResponse(
        id=vacancy.id,
        company_id=company.id,
        title=vacancy.title,
        company_name=company.company_name,
        company_country=company.country,
        location=vacancy.location,
        country=vacancy.country,
        employment_type=vacancy.employment_type,
        work_mode=vacancy.work_mode,
        salary=vacancy.salary,
        salary_min=vacancy.salary_min,
        salary_max=vacancy.salary_max,
        salary_currency=vacancy.salary_currency,
        posting_date=vacancy.posting_date,
        closing_date=vacancy.closing_date,
        first_seen_at=vacancy.first_seen_at,
        last_seen_at=vacancy.last_seen_at,
        application_url=_apply_link(vacancy),
        is_open=vacancy.is_open,
        opportunity_type=vacancy.opportunity_type or "job",
        field_of_study=vacancy.field_of_study,
        stipend_text=vacancy.stipend_text,
        verified_at=vacancy.verified_at,
    )


def _open_public(query):
    return query.filter(Company.deleted_at.is_(None), *public_role_clauses())


@router.get("/jobs/counts", response_model=OpportunityCountResponse)
@limiter.limit("60/minute")
def public_job_counts(request: Request, response: Response, db: Session = Depends(get_db)):
    """How many open stored rows there are of each opportunity type."""
    response.headers["Cache-Control"] = "public, max-age=60"
    rows = (
        _open_public(db.query(Vacancy.opportunity_type, func.count(Vacancy.id))
                     .join(Company, Company.id == Vacancy.company_id))
        .group_by(Vacancy.opportunity_type)
        .all()
    )
    counts = {kind: 0 for kind in OPPORTUNITY_TYPES}
    for kind, total in rows:
        key = kind if kind in counts else "job"
        counts[key] += int(total or 0)
    return OpportunityCountResponse(counts=counts)


@router.get("/jobs", response_model=PublicJobListResponse)
@limiter.limit("60/minute")
def list_public_jobs(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=80, description="Words in the job title"),
    country: str | None = Query(default=None, max_length=80, description="Employer country or the role's country"),
    employer: str | None = Query(default=None, max_length=80, description="Words in the employer name"),
    employment_type: str | None = Query(default=None, max_length=40, description="Exact stored employment type"),
    opportunity_type: str | None = Query(
        default=None, max_length=32,
        description="job, internship, learnership, bursary, or graduate_programme",
    ),
    max_age_days: int | None = Query(
        default=None, ge=1, le=365,
        description="Only roles last seen on the employer site within this many days",
    ),
    sort: str | None = Query(
        default=None, max_length=20,
        description="closing puts a stated closing date first. Anything else uses last seen.",
    ),
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100_000),
):
    """Open roles the scanner has already stored. No sign-in. No advert body."""
    response.headers["Cache-Control"] = "public, max-age=60"
    query = (
        db.query(Vacancy, Company)
        .join(Company, Company.id == Vacancy.company_id)
        .filter(Company.deleted_at.is_(None), *public_role_clauses())
    )
    if q and q.strip():
        phrases = expand_title_terms(q)
        likes = [Vacancy.title.ilike(_like_fragment(phrase)) for phrase in phrases]
        types = opportunity_types_for(q)
        if types:
            likes.append(Vacancy.opportunity_type.in_(types))
        query = query.filter(or_(*likes))
    named_country = bool(country and country.strip())
    if named_country:
        name = country.strip()[:80]
        query = query.filter((Company.country == name) | (Vacancy.country == name))
    if employer and employer.strip():
        query = query.filter(Company.company_name.ilike(_like_fragment(employer)))
    if employment_type and employment_type.strip():
        query = query.filter(Vacancy.employment_type == employment_type.strip()[:40])
    if opportunity_type and opportunity_type.strip():
        kind = opportunity_type.strip().lower().replace("-", "_").replace(" ", "_")
        if kind == "graduate_program":
            kind = "graduate_programme"
        if kind not in OPPORTUNITY_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Unknown opportunity type.")
        query = query.filter(Vacancy.opportunity_type == kind)
    if max_age_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        query = query.filter(Vacancy.last_seen_at >= cutoff)
    matched = query.count()
    if sort and sort.strip().lower() == "closing":
        order = (
            case((Vacancy.closing_date.is_(None), 1), else_=0),
            Vacancy.closing_date.asc(),
            Vacancy.last_seen_at.desc(),
        )
    else:
        order = (Vacancy.last_seen_at.desc(),)
    if not named_country:
        order = (flagship_role_rank(), *order)
    rows = query.order_by(*order).offset(offset).limit(limit).all()
    jobs = [_public_job(vacancy, company) for vacancy, company in rows]
    from app.services.employer_service import (
        RANKING_NOTE, SPONSORED_CAP, featured_matches, submitted_vacancy_ids,
    )
    sponsored_rows = featured_matches(db, query)
    sponsored = []
    sponsored_ids: set[str] = set()
    for vacancy, company, until in sponsored_rows:
        card = _public_job(vacancy, company)
        card.sponsored = True
        card.sponsored_until = until.date() if hasattr(until, "date") else until
        sponsored.append(card)
        sponsored_ids.add(vacancy.id)
    labels = submitted_vacancy_ids(db, [job.id for job in jobs] + [job.id for job in sponsored])
    for card in jobs:
        if card.id in labels:
            card.employer_submitted = True
            card.provenance = "employer-submitted"
        if card.id in sponsored_ids:
            card.sponsored = True
            match = next((item for item in sponsored if item.id == card.id), None)
            if match is not None:
                card.sponsored_until = match.sponsored_until
    for card in sponsored:
        if card.id in labels:
            card.employer_submitted = True
            card.provenance = "employer-submitted"
    return PublicJobListResponse(
        jobs=jobs,
        matched=matched,
        limit=limit,
        sponsored=sponsored,
        sponsored_cap=SPONSORED_CAP,
        ranking_note=RANKING_NOTE,
    )


def _plain_excerpt(text: str | None, limit: int = 1200) -> str | None:
    if not text:
        return None
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return None
    if len(plain) <= limit:
        return plain
    cut = plain[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def _public_summary(vacancy: Vacancy, company: Company) -> str:
    excerpt = _plain_excerpt(vacancy.description)
    if excerpt:
        return excerpt
    place = vacancy.location or vacancy.country or company.country
    bits = [f"{vacancy.title} at {company.company_name}."]
    if place:
        bits.append(f"Location: {place}.")
    if vacancy.opportunity_type and vacancy.opportunity_type != "job":
        bits.append(f"Type: {vacancy.opportunity_type.replace('_', ' ')}.")
    bits.append("The stored advert had no description text.")
    return " ".join(bits)


def _public_detail(vacancy: Vacancy, company: Company) -> PublicJobDetailResponse:
    job = _public_job(vacancy, company)
    if not is_publicly_listed(vacancy):
        job.is_open = False
    return PublicJobDetailResponse(**job.model_dump(), summary=_public_summary(vacancy, company))


def _load_stored_pair(db: Session, job_id: str) -> tuple[Vacancy, Company] | None:
    """The stored row, including one that has expired. Missing rows are None."""
    row = (
        db.query(Vacancy, Company)
        .join(Company, Company.id == Vacancy.company_id)
        .filter(Vacancy.id == job_id, Vacancy.deleted_at.is_(None), Company.deleted_at.is_(None))
        .one_or_none()
    )
    if row is None:
        return None
    return row[0], row[1]


def _load_public_pair(db: Session, job_id: str) -> tuple[Vacancy, Company] | None:
    pair = _load_stored_pair(db, job_id)
    if pair is None or not is_publicly_listed(pair[0]):
        return None
    return pair


@router.get("/jobs/suggest", response_model=JobSuggestResponse)
@limiter.limit("60/minute")
def suggest_public_jobs(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    q: str = Query(min_length=2, max_length=80),
):
    """Titles, employers and countries from open stored roles. Prefix match only."""
    response.headers["Cache-Control"] = "public, max-age=60"
    needle = _like_fragment(q)
    # A prefix is more useful than a contains-match for a short suggestion list.
    prefix = needle[1:] if needle.startswith("%") else needle

    def names(column):
        query = _open_public(
            db.query(column)
            .select_from(Vacancy)
            .join(Company, Company.id == Vacancy.company_id)
        )
        rows = query.filter(column.ilike(prefix)).distinct().limit(5).all()
        return [row[0] for row in rows if row[0]]

    return JobSuggestResponse(
        titles=names(Vacancy.title),
        employers=names(Company.company_name),
        countries=countries_flagship_first(names(Company.country)),
    )


@router.get("/jobs/facets", response_model=JobFacetsResponse)
@limiter.limit("30/minute")
def public_job_facets(request: Request, response: Response, db: Session = Depends(get_db)):
    """Countries and employment categories that have at least one open stored role."""
    response.headers["Cache-Control"] = "public, max-age=300"
    country_rows = (
        _open_public(db.query(Company.country, func.count(Vacancy.id))
                     .join(Company, Company.id == Vacancy.company_id))
        .group_by(Company.country)
        .all()
    )
    category_rows = (
        _open_public(db.query(Vacancy.employment_type, func.count(Vacancy.id))
                     .join(Company, Company.id == Vacancy.company_id))
        .filter(Vacancy.employment_type.isnot(None), Vacancy.employment_type != "")
        .group_by(Vacancy.employment_type)
        .all()
    )
    countries = [
        JobFacetCount(name=name, count=int(total))
        for name, total in country_rows
        if name and int(total) > 0
    ]
    categories = [
        JobFacetCount(name=name.strip(), count=int(total))
        for name, total in category_rows
        if name and name.strip() and len(name.strip()) <= 40 and int(total) >= 2
    ]
    countries.sort(key=lambda row: (0 if row.name == FLAGSHIP_COUNTRY else 1, -row.count, row.name))
    categories.sort(key=lambda row: (-row.count, row.name))
    return JobFacetsResponse(countries=countries, categories=categories[:40])


@router.get("/jobs/ids", response_model=JobIdListResponse)
@limiter.limit("30/minute")
def public_job_ids(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    max_age_days: int = Query(default=14, ge=1, le=60),
    limit: int = Query(default=1000, ge=1, le=2000),
    offset: int = Query(default=0, ge=0, le=20000),
):
    """Ids of open roles last seen within max_age_days, for the sitemap. Newest first."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    query = (
        _open_public(db.query(Vacancy.id).join(Company, Company.id == Vacancy.company_id))
        .filter(Vacancy.last_seen_at >= cutoff)
    )
    matched = query.count()
    rows = query.order_by(Vacancy.last_seen_at.desc()).offset(offset).limit(limit).all()
    return JobIdListResponse(ids=[row[0] for row in rows], matched=matched)


@router.get("/jobs/{job_id}", response_model=PublicJobDetailResponse)
@limiter.limit("60/minute")
def get_public_job(job_id: str, request: Request, response: Response, db: Session = Depends(get_db)):
    """One open stored role. An expired role is 410. A missing role is 404."""
    response.headers["Cache-Control"] = "public, max-age=60"
    pair = _load_stored_pair(db, job_id)
    if pair is None:
        if public_id_was_deleted(db, job_id):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This opportunity has closed.",
                headers={"X-Robots-Tag": "noindex"},
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="That open role is not stored.")
    if not is_publicly_listed(pair[0]):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This opportunity has closed.",
            headers={"X-Robots-Tag": "noindex"},
        )
    return _public_detail(*pair)


@router.get("/saved-opportunities", response_model=list[PublicJobDetailResponse])
@limiter.limit("60/minute")
def list_saved_opportunities(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Roles this person saved. A role that has since closed stays in the list and is marked closed."""
    private_short_cache(response)
    rows = (
        db.query(SavedOpportunity, Vacancy, Company)
        .join(Vacancy, Vacancy.id == SavedOpportunity.vacancy_id)
        .join(Company, Company.id == Vacancy.company_id)
        .filter(SavedOpportunity.user_id == user.id, Vacancy.deleted_at.is_(None), Company.deleted_at.is_(None))
        .order_by(SavedOpportunity.created_at.desc())
        .limit(100)
        .all()
    )
    return [_public_detail(vacancy, company) for _, vacancy, company in rows]


@router.post("/saved-opportunities", response_model=PublicJobDetailResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
def save_opportunity(
    body: SavedOpportunityCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pair = _load_public_pair(db, body.vacancy_id.strip())
    if pair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="That open role is not stored.")
    existing = (
        db.query(SavedOpportunity)
        .filter(SavedOpportunity.user_id == user.id, SavedOpportunity.vacancy_id == pair[0].id)
        .one_or_none()
    )
    if existing is None:
        count = db.query(SavedOpportunity).filter(SavedOpportunity.user_id == user.id).count()
        if count >= 100:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The saved list is full (100).")
        db.add(SavedOpportunity(user_id=user.id, vacancy_id=pair[0].id))
        db.commit()
    return _public_detail(*pair)


@router.delete("/saved-opportunities/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
def unsave_opportunity(
    vacancy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db.query(SavedOpportunity).filter(
        SavedOpportunity.user_id == user.id,
        SavedOpportunity.vacancy_id == vacancy_id,
    ).delete(synchronize_session=False)
    db.commit()


@router.get("/vacancies", response_model=list[VacancyResponse])
@limiter.limit("600/hour", key_func=user_or_ip_key)
def list_vacancies(request: Request, response: Response, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user),
                   q: str | None = Query(default=None, description="Search in title"),
                   is_open: bool | None = Query(default=True),
                   province: str | None = Query(
                       default=None, description="South African province, e.g. 'Gauteng' (best-effort field)."),
                   employment_type: str | None = Query(default=None, description="Substring match, e.g. 'Internship'."),
                   min_salary: int | None = Query(
                       default=None, ge=0, description="Monthly ZAR. Matches listings whose parsed salary_max is at least this."),
                   max_salary: int | None = Query(
                       default=None, ge=0, description="Monthly ZAR. Matches listings whose parsed salary_min is at most this."),
                   nqf_level: int | None = Query(
                       default=None, ge=1, le=10, description="Estimated NQF level (1-10) required by the listing."),
                   flagged: bool | None = Query(
                       default=None, description="True: only listings with a trust/safety flag. False: only listings with none."),
                   max_age_days: int | None = Query(
                       default=None, ge=1,
                       description="Only vacancies last seen within this many days (drops stale/old listings)."),
                   limit: int = Query(default=50, le=200), offset: int = Query(default=0, ge=0)):
    private_short_cache(response)
    query = db.query(Vacancy).options(*_LIST_DEFER)
    if user.role != "admin":
        query = query.filter(*public_role_clauses())
    elif is_open is False:
        query = query.filter(or_(Vacancy.status == "expired", Vacancy.is_open.is_(False)))
    elif is_open is not False:
        query = query.filter(*public_role_clauses())
    if q:
        query = query.filter(Vacancy.title.ilike(f"%{q}%"))
    if province:
        query = query.filter(Vacancy.province == province)
    if employment_type:
        query = query.filter(Vacancy.employment_type.ilike(f"%{employment_type}%"))
    if min_salary is not None:
        query = query.filter(Vacancy.salary_max.is_not(None), Vacancy.salary_max >= min_salary)
    if max_salary is not None:
        query = query.filter(Vacancy.salary_min.is_not(None), Vacancy.salary_min <= max_salary)
    if nqf_level is not None:
        query = query.filter(Vacancy.nqf_level == nqf_level)
    if max_age_days is not None:
        # Drop listings we haven't seen on the employer's careers page
        # recently. (The closing-date exclusion above already handles
        # outdated ads; this additionally drops listings that are merely
        # stale from the scanner's point of view.)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        query = query.filter(Vacancy.last_seen_at >= cutoff)
    if flagged is not None:
        # trust_flags is a JSON column -- filtering on "is the array non-empty"
        # portably across SQLite (tests) and Postgres (production) is awkward in
        # pure SQL, so this filters in Python over a bounded, already-ordered
        # window rather than adding a dialect-specific JSON expression.
        query = query.order_by(Vacancy.last_seen_at.desc()).limit(2000)
        candidates = [v for v in query.all() if bool(v.trust_flags) == flagged]
        return [VacancyResponse.model_validate(v) for v in candidates[offset:offset + limit]]
    query = query.order_by(Vacancy.last_seen_at.desc()).offset(offset).limit(limit)
    return [VacancyResponse.model_validate(v) for v in query.all()]


@router.get("/admin/vacancies", response_model=AdminVacancyListResponse)
def list_admin_vacancies(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    status_filter: str = Query(default="expired", alias="status", pattern="^(active|expired|all)$"),
    q: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Stored roles, including expired ones. Nothing is deleted."""
    active = (
        db.query(func.count(Vacancy.id))
        .join(Company, Company.id == Vacancy.company_id)
        .filter(Company.deleted_at.is_(None), *public_role_clauses())
        .scalar()
        or 0
    )
    expired = (
        db.query(func.count(Vacancy.id))
        .filter(*expired_role_clauses())
        .scalar()
        or 0
    )
    query = (
        db.query(Vacancy, Company)
        .join(Company, Company.id == Vacancy.company_id)
        .filter(Vacancy.deleted_at.is_(None), Company.deleted_at.is_(None))
    )
    if status_filter == "expired":
        query = query.filter(*expired_role_clauses())
    elif status_filter == "active":
        query = query.filter(*public_role_clauses())
    if q and q.strip():
        query = query.filter(Vacancy.title.ilike(f"%{q.strip()[:80]}%"))
    rows = query.order_by(Vacancy.expired_at.desc(), Vacancy.last_seen_at.desc()).limit(limit).all()
    return AdminVacancyListResponse(
        status=status_filter,
        active=int(active),
        expired=int(expired),
        rows=[
            AdminVacancyRow(
                id=vacancy.id,
                title=vacancy.title,
                company_name=company.company_name,
                company_id=company.id,
                status="active" if is_publicly_listed(vacancy) else "expired",
                expired_at=vacancy.expired_at,
                closing_date=vacancy.closing_date,
                lifecycle_status=vacancy.lifecycle_status,
                is_open=vacancy.is_open,
            )
            for vacancy, company in rows
        ],
    )


@router.get("/vacancies/{vacancy_id}", response_model=VacancyDetailResponse)
def get_vacancy(vacancy_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vac = db.get(Vacancy, vacancy_id)
    if vac is None or vac.deleted_at is not None:
        if public_id_was_deleted(db, vacancy_id):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This opportunity has closed.",
                headers={"X-Robots-Tag": "noindex"},
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found.")
    if user.role != "admin" and not is_publicly_listed(vac):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This opportunity has closed.",
            headers={"X-Robots-Tag": "noindex"},
        )
    return VacancyDetailResponse.model_validate(vac)


@router.post("/vacancies/{vacancy_id}/report", response_model=VacancyReportResponse,
             status_code=status.HTTP_201_CREATED)
def report_vacancy(vacancy_id: str, body: VacancyReportCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Candidate-facing "Report this opportunity" (scam / expired / incorrect /
    duplicate / misleading / other) -- queued for admin triage, never auto-acted on."""
    report = create_vacancy_report(db, user_id=user.id, vacancy_id=vacancy_id,
                                   category=body.category, details=body.details)
    return VacancyReportResponse.model_validate(report)


@router.get("/admin/vacancy-reports", response_model=list[VacancyReportResponse],
            dependencies=[Depends(require_admin)])
def list_vacancy_reports(db: Session = Depends(get_db),
                         status_filter: str | None = Query(default=None, alias="status")):
    q = db.query(VacancyReport)
    if status_filter:
        q = q.filter(VacancyReport.status == status_filter)
    return [VacancyReportResponse.model_validate(r)
            for r in q.order_by(VacancyReport.created_at.desc()).all()]


@router.get("/admin/vacancies/duplicates", response_model=list[DuplicateGroupResponse],
            dependencies=[Depends(require_admin)])
def list_duplicate_vacancies(db: Session = Depends(get_db),
                             company_id: str | None = Query(default=None)):
    groups = find_duplicate_groups(db, company_id=company_id)
    return [
        DuplicateGroupResponse(
            keep=VacancyResponse.model_validate(g.keep),
            duplicates=[VacancyResponse.model_validate(d) for d in g.duplicates],
        )
        for g in groups
    ]


@router.get("/admin/vacancies/external-id-duplicates",
            response_model=list[ExternalIdDuplicateGroupResponse],
            dependencies=[Depends(require_admin)])
def list_external_id_duplicates(db: Session = Depends(get_db),
                                company_id: str | None = Query(default=None)):
    """Open rows that share an employer job id. Does not close or delete any row."""
    return [ExternalIdDuplicateGroupResponse.model_validate(group)
            for group in find_external_id_groups(db, company_id=company_id)]


@router.post("/admin/vacancies/merge", response_model=MergeDuplicatesResponse,
             dependencies=[Depends(require_admin)])
def merge_duplicate_vacancies(body: MergeDuplicatesRequest, db: Session = Depends(get_db)):
    merged = merge_duplicates(db, keep_id=body.keep_id, duplicate_ids=body.duplicate_ids)
    return MergeDuplicatesResponse(merged=merged)
