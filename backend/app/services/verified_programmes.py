"""Store programme names read from an employer's own page.

The file lists only names that were on that page, with the sentence that
sat under the name. A closing date is stored only when the page stated one
and that date is still open. A row is attached to an inactive source so the scanner
keeps reading the employer's careers board. A company that is not already in the directory
is skipped. Nothing here creates an employer.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.services.opportunity_type import OPPORTUNITY_TYPES
from app.services.scan_service import ensure_source

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sa_verified_programmes.json"
EXTERNAL_PREFIX = "verified:"
VERIFIED_ATS = "verified_page"
_PROGRAMME_TYPES = tuple(kind for kind in OPPORTUNITY_TYPES if kind != "job")


def external_id_for(company_name: str, title: str, source_url: str) -> str:
    raw = f"{company_name.strip()}|{title.strip()}|{source_url.strip()}".encode()
    return EXTERNAL_PREFIX + hashlib.sha256(raw).hexdigest()[:32]


def load_programme_file(path: Path | None = None) -> tuple[datetime, list[dict]]:
    payload = json.loads((path or DATA_PATH).read_text(encoding="utf-8"))
    verified_on = datetime.strptime(payload["verified_on"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return verified_on, list(payload["records"])


def import_verified_programmes(
    bind: Engine,
    *,
    records: list[dict] | None = None,
    verified_on: datetime | None = None,
) -> dict[str, int]:
    """Insert or update the verified rows. Safe to run on every boot."""
    if records is None:
        verified_on, records = load_programme_file()
    if verified_on is None:
        verified_on = datetime.now(timezone.utc)
    counts = {
        "created": 0,
        "updated": 0,
        "skipped_missing_company": 0,
        "skipped_duplicate_title": 0,
        "skipped_invalid": 0,
        "skipped_expired": 0,
        "skipped_closed": 0,
    }
    db = Session(bind=bind)
    try:
        for record in records:
            outcome = _store_one(db, record, verified_on)
            counts[outcome] += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return counts


def _store_one(db: Session, record: dict, verified_on: datetime) -> str:
    title = (record.get("title") or "").strip()
    company_name = (record.get("company_name") or "").strip()
    country = (record.get("country") or "").strip()
    source_url = (record.get("source_url") or "").strip()
    kind = (record.get("opportunity_type") or "").strip()
    if not title or not company_name or not country or not source_url.startswith("https://"):
        return "skipped_invalid"
    if kind not in _PROGRAMME_TYPES or len(title) > 300:
        return "skipped_invalid"
    field = _bounded(record.get("field_of_study"), 400)
    stipend = _bounded(record.get("stipend_text"), 240)
    description = _clean(record.get("description"))
    qualifications = _clean(record.get("qualifications"))
    companies = (
        db.query(Company)
        .filter(func.lower(func.trim(Company.company_name)) == company_name.lower())
        .filter(Company.country == country)
        .filter(Company.deleted_at.is_(None))
        .all()
    )
    if len(companies) != 1:
        return "skipped_missing_company"
    company = companies[0]
    if company.careers_url:
        ensure_source(db, company)
    source = _verified_source(db, company, source_url, verified_on)
    external_id = external_id_for(company.company_name, title, source_url)
    digest = hashlib.sha256(f"{title}|{source_url}|{kind}".encode()).hexdigest()
    existing = (
        db.query(Vacancy)
        .filter(Vacancy.external_id == external_id, Vacancy.deleted_at.is_(None))
        .first()
    )
    if existing is not None and "manual_close" in list(existing.quality_flags or []):
        # Closed after a check found no sign it is open. A boot must not reopen it.
        return "skipped_closed"
    if existing is None:
        same_title = (
            db.query(Vacancy)
            .filter(
                Vacancy.company_id == company.id,
                Vacancy.deleted_at.is_(None),
                Vacancy.is_open.is_(True),
                func.lower(func.trim(Vacancy.title)) == title.lower(),
            )
            .first()
        )
        if same_title is not None:
            return "skipped_duplicate_title"
        from app.services.opportunity_tombstone import listing_was_deleted
        if listing_was_deleted(
            db,
            company_id=company.id,
            external_id=external_id,
            source_url=source_url,
            canonical_url=source_url,
            application_url=source_url,
            fingerprint=None,
            board_url=None,
        ):
            return "skipped_expired"
        from app.services.opportunity_expiry import closing_value_has_passed
        if closing_value_has_passed(_stated_closing(record.get("closing_date"), verified_on)):
            return "skipped_expired"
        existing = Vacancy(
            company_id=company.id,
            source_id=source.id,
            external_id=external_id,
            title=title,
            content_hash=digest,
            is_open=True,
            first_seen_at=verified_on,
            last_seen_at=verified_on,
        )
        db.add(existing)
        outcome = "created"
    else:
        outcome = "updated"
    existing.source_id = source.id
    existing.title = title
    existing.opportunity_type = kind
    existing.field_of_study = field
    existing.stipend_text = stipend
    existing.description = description
    existing.qualifications = qualifications
    existing.country = country
    existing.source_url = source_url
    existing.application_url = source_url
    existing.closing_date = _stated_closing(record.get("closing_date"), verified_on)
    existing.posting_date = None
    existing.content_hash = digest
    existing.fingerprint = digest
    from app.services.opportunity_expiry import closing_has_passed, mark_active, mark_expired
    if closing_has_passed(existing.closing_date):
        mark_expired(existing, verified_on)
    else:
        mark_active(existing)
    existing.verification_state = existing.verification_state or "DISCOVERED"
    existing.opportunity_reviewed = True
    existing.verified_at = verified_on
    existing.last_seen_at = verified_on
    return outcome


def _verified_source(db: Session, company: Company, source_url: str, verified_on: datetime) -> VacancySource:
    source = (
        db.query(VacancySource)
        .filter(
            VacancySource.company_id == company.id,
            VacancySource.ats_type == VERIFIED_ATS,
            VacancySource.url == source_url,
            VacancySource.deleted_at.is_(None),
        )
        .first()
    )
    if source is not None:
        source.active = False
        source.last_checked = verified_on
        source.robots_allowed = True
        return source
    careers = (
        db.query(VacancySource)
        .filter(VacancySource.company_id == company.id, VacancySource.deleted_at.is_(None))
        .order_by(VacancySource.created_at.asc(), VacancySource.id.asc())
        .first()
    )
    created = verified_on
    if careers is not None and careers.created_at is not None:
        earlier = careers.created_at
        if earlier.tzinfo is None:
            earlier = earlier.replace(tzinfo=timezone.utc)
        created = earlier + timedelta(seconds=1)
    source = VacancySource(
        company_id=company.id,
        url=source_url,
        ats_type=VERIFIED_ATS,
        active=False,
        robots_allowed=True,
        last_checked=verified_on,
        last_status="ok",
        created_at=created,
    )
    db.add(source)
    db.flush()
    return source


def _stated_closing(value, verified_on: datetime) -> date | None:
    """Keep a closing date only when the page stated an ISO date that is still open."""
    if value is None:
        return None
    text = str(value).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        day = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None
    if day < verified_on.date():
        return None
    return day


def _clean(value) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _bounded(value, limit: int) -> str | None:
    text = _clean(value)
    if text is None or len(text) > limit:
        return None
    return text
