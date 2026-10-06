"""Scan orchestration (blueprint sections 13, 22 & 23).

Ties the pieces together: pick a source, respect robots, fetch via the right
strategy, normalise + deduplicate vacancies, classify requirements, detect closed
roles, and record status/errors for change detection. Deterministic and idempotent:
re-scanning does not create duplicates.

A role is closed only with a reason we can defend: the listing itself says it
is closed, its closing date has passed (separate nightly job), or it was
missing from two successful scans in a row. One empty or failed fetch never
closes anything.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.scan_log import ScanLog
from app.models.vacancy import VacancySource, Vacancy, VacancyRequirement
from app.scraper.adapter import adapter_for
from app.scraper.base import detect_ats
from app.scraper.errors import NEEDS_REVIEW_AFTER, classify_fetch_error, http_status_of, is_permanent
from app.scraper.static_html import BotChallengeError
from app.scraper.ssrf import SsrfBlocked, assert_safe_fetch_url
from app.services.trust_service import scan_for_trust_flags
from app.scraper.politeness import RobotsChecker


# Two successful scans that omit a role, then it is marked REMOVED.
MISS_CLOSE_AFTER = 2

_COPY_IF_PRESENT = (
    "external_id", "department", "location", "city", "country", "work_mode",
    "employment_type", "salary", "salary_currency", "posting_date", "closing_date",
    "description", "requirements_text", "qualifications", "experience",
    "application_url", "source_url", "canonical_url", "source_domain", "province",
    "salary_min", "salary_max", "nqf_level",
)


@dataclass
class ScanReport:
    source_id: str
    status: str
    created: int = 0
    updated: int = 0
    closed: int = 0
    total_seen: int = 0
    duplicates_prevented: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    # Ids of vacancies newly created by this scan (not previously seen), so callers
    # can alert candidates about them without re-querying "what changed".
    created_vacancy_ids: list[str] = field(default_factory=list)


def ensure_source(db: Session, company: Company) -> VacancySource | None:
    """Return the company's default vacancy source, creating one from its careers URL."""
    source = (db.query(VacancySource).filter(VacancySource.company_id == company.id)
              .order_by(VacancySource.created_at.asc(), VacancySource.id.asc()).first())
    if source is not None:
        return source
    if not company.careers_url:
        return None
    ats_type, config = detect_ats(company.careers_url)
    source = VacancySource(company_id=company.id, url=company.careers_url,
                           ats_type=ats_type, config=config)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def _make_client() -> httpx.Client:
    return httpx.Client(timeout=settings.URL_TEST_TIMEOUT_SECONDS, follow_redirects=False,
                        headers={"User-Agent": settings.URL_TEST_USER_AGENT})


def _write_log(db: Session, source: VacancySource, report: ScanReport, started: float,
               *, error_category: str | None = None, http_status: int | None = None) -> None:
    elapsed = int((time.monotonic() - started) * 1000)
    db.add(ScanLog(
        company_id=source.company_id,
        source_id=source.id,
        url=(source.url or "")[:2000] or None,
        status=(report.status or "")[:40],
        error_category=(error_category or "")[:40] or None,
        pages_scanned=1 if report.status not in ("no_url", "disabled") else 0,
        vacancies_discovered=report.total_seen,
        vacancies_new=report.created,
        vacancies_updated=report.updated,
        duplicates_prevented=report.duplicates_prevented,
        vacancies_closed=report.closed,
        duration_ms=max(elapsed, 0),
        http_status=http_status if http_status is not None else source.http_status,
        parser_used=source.parser_used,
        finished_at=datetime.now(timezone.utc),
    ))


@dataclass
class FetchOutcome:
    """What the network half of a scan found. Built without a DB session, so
    the batch runner can fetch several sources on worker threads and write the
    results on the request's own session afterwards."""
    kind: str                      # ok | robots_disallowed | javascript_required | blocked | error
    started: float
    now: datetime
    robots_allowed: bool | None = None
    ats_type: str | None = None
    config: dict | None = None
    parser_used: str | None = None
    raw_list: list = field(default_factory=list)
    exc: BaseException | None = None


@dataclass
class SourceSnapshot:
    """The fields an adapter reads (``url``, ``config``), copied off the ORM row
    so a worker thread never touches the session."""
    id: str
    url: str
    config: dict | None = None
    ats_type: str | None = None


def snapshot_of(source: VacancySource) -> SourceSnapshot:
    return SourceSnapshot(id=source.id, url=source.url, config=dict(source.config or {}) or None,
                          ats_type=source.ats_type)


def fetch_source(source, client: httpx.Client, check_robots: bool = True,
                 now: datetime | None = None, started: float | None = None) -> FetchOutcome:
    """robots.txt, ATS detection and the page/API fetch. No database access.

    ``source`` only needs ``url`` (and ``config``, which is recomputed here).
    Expected fetch failures come back as ``kind="error"`` with the exception;
    anything else propagates, as it did when this lived inside scan_source.
    """
    out = FetchOutcome(kind="ok", started=time.monotonic() if started is None else started,
                       now=now or datetime.now(timezone.utc))
    if check_robots:
        allowed = RobotsChecker(client).is_allowed(source.url)
        out.robots_allowed = allowed
        if not allowed:
            out.kind = "robots_disallowed"
            out.parser_used = getattr(source, "ats_type", None)
            return out

    # Re-classify on every scan so a URL that moved onto a public JSON
    # feed (Workday, Oracle, Breezy, …) is not stuck on an old "js" or
    # "static" label from the day the source row was created.
    ats_type, config = detect_ats(source.url)
    out.ats_type, out.config, out.parser_used = ats_type, config, ats_type
    if ats_type == "js" and not settings.JS_RENDER_ENABLED:
        out.kind = "javascript_required"
        return out
    probe = SourceSnapshot(id=getattr(source, "id", ""), url=source.url, config=config,
                           ats_type=ats_type)
    try:
        assert_safe_fetch_url(source.url)
        adapter = adapter_for(ats_type)
        out.parser_used = adapter.name
        out.raw_list = adapter.discover(probe, client)
    except BotChallengeError:
        out.kind = "blocked"
    except (httpx.HTTPStatusError, httpx.TransportError, ValueError, SsrfBlocked) as exc:
        out.kind = "error"
        out.exc = exc
    return out


def scan_source(db: Session, source: VacancySource, client: httpx.Client | None = None,
                check_robots: bool = True) -> ScanReport:
    report = ScanReport(source_id=source.id, status="ok")
    owns_client = client is None
    if owns_client:
        client = _make_client()
    now = datetime.now(timezone.utc)
    started = time.monotonic()
    try:
        if source.active is False:
            source.last_checked = now
            source.scraper_status = "DISABLED"
            source.last_status = "disabled"
            report.status = "disabled"
            _write_log(db, source, report, started, error_category="DISABLED")
            db.commit()
            return report
        outcome = fetch_source(source, client, check_robots=check_robots, now=now, started=started)
        return apply_fetch(db, source, outcome)
    finally:
        if owns_client:
            client.close()


def apply_fetch(db: Session, source: VacancySource, outcome: FetchOutcome) -> ScanReport:
    """Write one fetch's result: vacancies, misses, source status and the scan log."""
    report = ScanReport(source_id=source.id, status="ok")
    now = outcome.now
    started = outcome.started
    if outcome.robots_allowed is not None:
        source.robots_allowed = outcome.robots_allowed
    if outcome.kind == "robots_disallowed":
        source.last_status = "robots_disallowed"
        source.scraper_status = "REQUIRES_REVIEW"
        source.error_category = "ROBOTS_DISALLOWED"
        source.last_checked = now
        source.parser_used = source.ats_type
        report.status = "robots_disallowed"
        _write_log(db, source, report, started, error_category="ROBOTS_DISALLOWED")
        db.commit()
        return report

    source.ats_type = outcome.ats_type
    source.config = outcome.config
    source.parser_used = outcome.parser_used
    if outcome.kind == "javascript_required":
        source.last_checked = now
        source.last_status = "javascript_required"
        source.scraper_status = "JAVASCRIPT_REQUIRED"
        source.error_category = "JAVASCRIPT_REQUIRED"
        source.last_error = "This board needs a browser. Rendering is off on the free host."
        report.status = "javascript_required"
        report.warnings.append(source.last_error)
        _write_log(db, source, report, started, error_category="JAVASCRIPT_REQUIRED")
        db.commit()
        return report
    if outcome.kind == "blocked":
        # A WAF challenge is not an empty board and not a dead link.
        # Leave the failure streak alone so the URL is not marked broken.
        source.last_checked = now
        source.last_status = "blocked"
        source.scraper_status = "BLOCKED"
        source.error_category = "BLOCKED"
        source.last_error = None
        report.status = "blocked"
        report.warnings.append("Host returned a bot challenge; link left unchanged.")
        _write_log(db, source, report, started, error_category="BLOCKED")
        db.commit()
        return report
    if outcome.kind == "error":
        return _record_failure(db, source, report, now, outcome.exc, started)

    adapter = adapter_for(source.ats_type)
    raw_list = outcome.raw_list
    company = db.get(Company, source.company_id)
    company_name = company.company_name if company else None
    company_country = company.country if company else None
    seen_ids: set[str] = set()
    for raw in raw_list:
        raw = adapter.extract(raw)
        if not raw.title:
            continue
        fields = adapter.normalize(
            raw, company_id=source.company_id, company_name=company_name,
            company_country=company_country, source_url=source.url,
        )
        if "title" in adapter.validate(fields):
            continue
        existing = _find_existing(db, source, fields)
        if existing:
            was_open = existing.is_open
            _apply_fields(existing, fields, now)
            _replace_requirements(db, existing, fields["requirement_rows"])
            existing.last_seen_at = now
            seen_ids.add(existing.id)
            report.updated += 1
            report.duplicates_prevented += 1
            if fields["lifecycle_status"] == "CLOSED" and was_open:
                report.closed += 1
        else:
            trust_flags = scan_for_trust_flags(
                title=fields["title"], description=fields["description"],
                salary_min=fields["salary_min"], salary_max=fields["salary_max"],
                application_url=fields["application_url"], source_url=fields["source_url"],
            )
            vac = Vacancy(
                company_id=source.company_id, source_id=source.id,
                raw_content=fields["raw_content"], trust_flags=trust_flags,
                is_open=fields["is_open"], lifecycle_status=fields["lifecycle_status"],
                verification_state="DISCOVERED", consecutive_misses=0,
                first_seen_at=now, last_seen_at=now,
            )
            _apply_fields(vac, fields, now)
            db.add(vac)
            db.flush()
            for row in fields["requirement_rows"]:
                db.add(VacancyRequirement(vacancy_id=vac.id, **row))
            seen_ids.add(vac.id)
            report.created += 1
            report.created_vacancy_ids.append(vac.id)
            if fields["lifecycle_status"] == "CLOSED":
                report.closed += 1

    # Missing from a successful, non-empty scan increments a counter.
    # The row is closed only after MISS_CLOSE_AFTER such scans. An empty
    # result is "couldn't read the page", not "every role closed".
    if raw_list:
        stale = (db.query(Vacancy)
                 .filter(Vacancy.source_id == source.id, Vacancy.is_open.is_(True))
                 .all())
        for vac in stale:
            if vac.id in seen_ids:
                continue
            vac.consecutive_misses = (vac.consecutive_misses or 0) + 1
            if vac.consecutive_misses >= MISS_CLOSE_AFTER:
                vac.is_open = False
                vac.lifecycle_status = "REMOVED"
                report.closed += 1

    prev_count = source.last_vacancy_count
    report.total_seen = len(raw_list)
    source.last_checked = now
    source.last_success_at = now
    source.last_vacancy_count = len(raw_list)
    source.consecutive_failures = 0
    source.last_error = None
    source.error_category = None
    source.http_status = None
    source.response_time_ms = int((time.monotonic() - started) * 1000)
    source.duplicates_prevented = (source.duplicates_prevented or 0) + report.duplicates_prevented
    source.last_status = "ok" if raw_list else "empty"
    if raw_list:
        source.empty_streak = 0
        source.last_vacancy_found_at = now
        source.scraper_status = "SUCCESS"
    else:
        source.empty_streak = (source.empty_streak or 0) + 1
        if prev_count and prev_count > 0:
            source.scraper_status = "SITE_CHANGED"
            source.error_category = "SITE_STRUCTURE_CHANGED"
            report.status = "empty"
            report.warnings.append("Source returned no vacancies; may indicate a structure change.")
            _alert_admins(db, source, "structure_changed",
                          "Careers page may have changed",
                          f"Source '{source.url}' returned 0 vacancies but previously had "
                          f"{prev_count}. It may have changed structure or moved.")
        else:
            source.scraper_status = "NO_VACANCIES"
            report.status = "empty"
            report.warnings.append("Source returned no vacancies.")
    _write_log(db, source, report, started)
    db.commit()
    return report


def _find_existing(db: Session, source: VacancySource, fields: dict) -> Vacancy | None:
    existing = (db.query(Vacancy)
                .filter(Vacancy.company_id == source.company_id,
                        Vacancy.fingerprint == fields["fingerprint"])
                .first())
    if existing is None and fields["external_id"]:
        existing = (db.query(Vacancy)
                    .filter(Vacancy.company_id == source.company_id,
                            Vacancy.external_id == fields["external_id"])
                    .first())
    if existing is None:
        existing = (db.query(Vacancy)
                    .filter(Vacancy.company_id == source.company_id,
                            Vacancy.content_hash == fields["content_hash"])
                    .first())
    return existing


def _apply_fields(vac: Vacancy, fields: dict, now: datetime) -> None:
    vac.title = fields["title"]
    vac.content_hash = fields["content_hash"]
    vac.fingerprint = fields["fingerprint"]
    vac.quality_score = fields["quality_score"]
    for key in _COPY_IF_PRESENT:
        value = fields[key]
        if value is not None:
            setattr(vac, key, value)
    vac.verification_state = vac.verification_state or "DISCOVERED"
    vac.consecutive_misses = 0
    vac.last_seen_at = now
    if fields["lifecycle_status"] == "CLOSED":
        vac.is_open = False
        vac.lifecycle_status = "CLOSED"
    else:
        vac.is_open = True
        vac.lifecycle_status = "ACTIVE"


def _replace_requirements(db: Session, vac: Vacancy, rows: list[dict]) -> None:
    db.query(VacancyRequirement).filter(VacancyRequirement.vacancy_id == vac.id).delete(
        synchronize_session=False,
    )
    for row in rows:
        db.add(VacancyRequirement(vacancy_id=vac.id, **row))


def _alert_admins(db, source, alert_type, title, body) -> None:
    from app.models.company import Company as _Company
    from app.services.notification_service import notify_admins
    company = db.get(_Company, source.company_id)
    prefix = f"[{company.company_name}] " if company else ""
    notify_admins(db, type="source_alert", title=prefix + title, body=body,
                  related_type="vacancy_source")


def _record_failure(db, source, report, now, exc: BaseException, started: float) -> ScanReport:
    last_status, category, scraper_status = classify_fetch_error(exc)
    source.last_checked = now
    source.last_status = last_status
    source.error_category = category
    source.scraper_status = scraper_status
    source.http_status = http_status_of(exc)
    source.consecutive_failures = (source.consecutive_failures or 0) + 1
    source.failure_count = (source.failure_count or 0) + 1
    source.last_error = str(exc)[:1000]
    source.response_time_ms = int((time.monotonic() - started) * 1000)
    if is_permanent(category) and source.consecutive_failures >= NEEDS_REVIEW_AFTER:
        # Same dead answer several scans in a row: park it for a person to look at.
        # The queue retries it weekly (scan_runner.due_after_hours), not every cycle.
        source.scraper_status = "NEEDS_REVIEW"
    report.status = last_status
    report.error = str(exc)
    # Edge-triggered alert: fire once when failures reach the threshold.
    if source.consecutive_failures == settings.SOURCE_FAILURE_ALERT_THRESHOLD:
        _alert_admins(db, source, "failure", "Careers source is failing",
                      f"Source '{source.url}' has failed {source.consecutive_failures} times "
                      f"in a row ({category}): {str(exc)[:200]}")
    _write_log(db, source, report, started, error_category=category, http_status=source.http_status)
    db.commit()
    return report


def scan_company(db: Session, company: Company, client: httpx.Client | None = None,
                 check_robots: bool = True) -> list[ScanReport]:
    source = ensure_source(db, company)
    if source is None:
        return [ScanReport(source_id="", status="no_url", error="Company has no careers URL.")]
    return [scan_source(db, source, client=client, check_robots=check_robots)]
