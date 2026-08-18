"""Scan orchestration (blueprint sections 13, 22 & 23).

Ties the pieces together: pick a source, respect robots, fetch via the right
strategy, normalise + deduplicate vacancies, classify requirements, detect closed
roles, and record status/errors for change detection. Deterministic and idempotent:
re-scanning does not create duplicates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.vacancy import VacancySource, Vacancy, VacancyRequirement
from app.scraper.base import detect_ats, get_strategy
from app.scraper.extract import normalize_date, infer_work_mode, content_hash, classify_requirements
from app.scraper.politeness import RobotsChecker


@dataclass
class ScanReport:
    source_id: str
    status: str
    created: int = 0
    updated: int = 0
    closed: int = 0
    total_seen: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def ensure_source(db: Session, company: Company) -> VacancySource | None:
    """Return the company's default vacancy source, creating one from its careers URL."""
    source = db.query(VacancySource).filter(VacancySource.company_id == company.id).first()
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
    return httpx.Client(timeout=settings.URL_TEST_TIMEOUT_SECONDS, follow_redirects=True,
                        headers={"User-Agent": settings.URL_TEST_USER_AGENT})


def scan_source(db: Session, source: VacancySource, client: httpx.Client | None = None,
                check_robots: bool = True) -> ScanReport:
    report = ScanReport(source_id=source.id, status="ok")
    owns_client = client is None
    if owns_client:
        client = _make_client()
    now = datetime.now(timezone.utc)
    try:
        if check_robots:
            allowed = RobotsChecker(client).is_allowed(source.url)
            source.robots_allowed = allowed
            if not allowed:
                source.last_status = "robots_disallowed"
                source.last_checked = now
                report.status = "robots_disallowed"
                db.commit()
                return report

        strategy = get_strategy(source.ats_type)
        try:
            raw_list = strategy.fetch(source, client)
        except httpx.HTTPStatusError as exc:
            return _record_failure(db, source, report, now, "http_error", str(exc))
        except (httpx.TransportError, ValueError) as exc:
            return _record_failure(db, source, report, now, "parse_error", str(exc))

        seen_ids: set[str] = set()
        for raw in raw_list:
            if not raw.title:
                continue
            chash = content_hash(source.company_id, raw)
            existing = (db.query(Vacancy)
                        .filter(Vacancy.company_id == source.company_id, Vacancy.content_hash == chash)
                        .first())
            if existing is None and raw.external_id:
                existing = (db.query(Vacancy)
                            .filter(Vacancy.source_id == source.id,
                                    Vacancy.external_id == raw.external_id)
                            .first())
            if existing:
                existing.last_seen_at = now
                existing.is_open = True
                seen_ids.add(existing.id)
                report.updated += 1
            else:
                vac = Vacancy(
                    company_id=source.company_id, source_id=source.id,
                    external_id=raw.external_id, title=raw.title[:300],
                    department=raw.department, location=raw.location,
                    work_mode=infer_work_mode(raw), employment_type=raw.employment_type,
                    salary=raw.salary, posting_date=normalize_date(raw.posting_date),
                    closing_date=normalize_date(raw.closing_date),
                    description=raw.description, application_url=raw.application_url,
                    source_url=raw.source_url or source.url,
                    raw_content=str(raw.raw)[:100000], content_hash=chash,
                    is_open=True, first_seen_at=now, last_seen_at=now,
                )
                db.add(vac)
                db.flush()
                for r in classify_requirements(raw.description):
                    db.add(VacancyRequirement(vacancy_id=vac.id, **r))
                seen_ids.add(vac.id)
                report.created += 1

        # Change detection: roles previously open for this source but not seen now
        # are closed — BUT ONLY when this scan actually returned a listing. An empty
        # result is treated as "couldn't read the page this time" (JS shell, cookie
        # wall, transient 200, heuristic miss), NOT "every role closed at once" —
        # otherwise a single flaky fetch would wipe a company's good vacancies.
        if raw_list:
            stale = (db.query(Vacancy)
                     .filter(Vacancy.source_id == source.id, Vacancy.is_open.is_(True))
                     .all())
            for vac in stale:
                if vac.id not in seen_ids:
                    vac.is_open = False
                    report.closed += 1

        prev_count = source.last_vacancy_count
        report.total_seen = len(raw_list)
        source.last_checked = now
        source.last_vacancy_count = len(raw_list)
        source.consecutive_failures = 0
        source.last_error = None
        source.last_status = "ok" if raw_list else "empty"
        if not raw_list:
            report.status = "empty"
            report.warnings.append("Source returned no vacancies; may indicate a structure change.")
            # Structure-change signal: had vacancies before, now none.
            if prev_count and prev_count > 0:
                _alert_admins(db, source, "structure_changed",
                              "Careers page may have changed",
                              f"Source '{source.url}' returned 0 vacancies but previously had "
                              f"{prev_count}. It may have changed structure or moved.")
        db.commit()
        return report
    finally:
        if owns_client:
            client.close()


def _alert_admins(db, source, alert_type, title, body) -> None:
    from app.models.company import Company as _Company
    from app.services.notification_service import notify_admins
    company = db.get(_Company, source.company_id)
    prefix = f"[{company.company_name}] " if company else ""
    notify_admins(db, type="source_alert", title=prefix + title, body=body,
                  related_type="vacancy_source")


def _record_failure(db, source, report, now, status_str, error) -> ScanReport:
    source.last_checked = now
    source.last_status = status_str
    source.consecutive_failures = (source.consecutive_failures or 0) + 1
    source.last_error = error[:1000]
    report.status = status_str
    report.error = error
    # Edge-triggered alert: fire once when failures reach the threshold.
    if source.consecutive_failures == settings.SOURCE_FAILURE_ALERT_THRESHOLD:
        _alert_admins(db, source, "failure", "Careers source is failing",
                      f"Source '{source.url}' has failed {source.consecutive_failures} times "
                      f"in a row ({status_str}): {error[:200]}")
    db.commit()
    return report


def scan_company(db: Session, company: Company, client: httpx.Client | None = None,
                 check_robots: bool = True) -> list[ScanReport]:
    source = ensure_source(db, company)
    if source is None:
        return [ScanReport(source_id="", status="no_url", error="Company has no careers URL.")]
    return [scan_source(db, source, client=client, check_robots=check_robots)]
