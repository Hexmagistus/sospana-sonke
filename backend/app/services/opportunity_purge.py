"""Delete expired opportunities after a private backup.

An opportunity is due when its closing day has ended in South Africa, or the
scanner has marked it closed or gone. Public pages already hide those rows.
This job removes them.

Backup location, written and read back before any delete:

- Production (``STORAGE_BACKEND=auto`` and ``ENV=production``) stores the
  gzip JSON in the private ``stored_files`` table. No public route serves
  that key.
- ``STORAGE_BACKEND=s3`` stores the same key in the configured private bucket.
- Otherwise the file is under ``STORAGE_DIR``.

The key prefix is ``private/expired-opportunities/``. The archive holds the
rows being deleted. The tombstone that remains is only a hash and a timestamp.

Order: write the archive, read it back, end featured placements, delete
bookmarks, click totals and other rows that reference the vacancy, write
tombstones, then delete the vacancies. A backup that does not read back
stops the run with every row still in place.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import tempfile
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.admin_ops import AdminAuditLog
from app.models.application import Application, ApplicationAnswer, ApplicationEvent
from app.models.document import CoverLetter, CVVersion
from app.models.interview import InterviewPrep
from app.models.match import CandidateMatch
from app.models.opportunity_tombstone import OpportunityTombstone
from app.models.organisation import EmployerEntitlement, EmployerOpportunity
from app.models.saved_opportunity import SavedOpportunity
from app.models.usage_count import UsageClickDaily
from app.models.vacancy import Vacancy, VacancyRequirement, VacancySource
from app.models.vacancy_report import VacancyReport
from app.services.opportunity_expiry import due_for_deletion_clauses, sa_today
from app.services.opportunity_tombstone import identity_hashes, public_id_hash
from app.services.storage import get_storage

# Cron has no signed-in administrator. The audit column is a 36-character id.
_SYSTEM_ACTOR = "00000000-0000-0000-0000-000000000000"
_CHUNK = 200


def _chunks(values: list[str], size: int = _CHUNK):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _plain(obj) -> dict:
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            data[column.name] = value.isoformat()
        elif isinstance(value, date):
            data[column.name] = value.isoformat()
        else:
            data[column.name] = value
    return data


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Cannot encode {type(value).__name__}")


class _Archive:
    def __init__(self, path: str) -> None:
        self.path = path
        self._raw = open(path, "wb")
        self._gz = gzip.GzipFile(fileobj=self._raw, mode="wb")
        self._first = True
        self._gz.write(b"{")

    def field(self, name: str, value) -> None:
        self._gz.write(json.dumps(name).encode())
        self._gz.write(b":")
        self._gz.write(json.dumps(value, default=_json_default).encode())
        self._gz.write(b",")

    def start_array(self, name: str) -> None:
        self._gz.write(json.dumps(name).encode())
        self._gz.write(b":[")
        self._first = True

    def item(self, obj: dict) -> None:
        if not self._first:
            self._gz.write(b",")
        self._first = False
        self._gz.write(json.dumps(obj, default=_json_default, separators=(",", ":")).encode())

    def end_array(self, last: bool) -> None:
        self._gz.write(b"]" if last else b"],")

    def close(self) -> bytes:
        self._gz.write(b"}")
        self._gz.close()
        self._raw.close()
        with open(self.path, "rb") as handle:
            return handle.read()


def _write_query(archive: _Archive, rows) -> int:
    count = 0
    for row in rows:
        archive.item(_plain(row))
        count += 1
    return count


def _backup(db: Session, ids: list[str], when: datetime) -> tuple[str, dict]:
    stamp = when.strftime("%Y%m%dT%H%M%SZ")
    key = f"private/expired-opportunities/{stamp}-{len(ids)}.json.gz"
    handle = tempfile.NamedTemporaryFile(prefix="expired-opportunities-", suffix=".json.gz", delete=False)
    path = handle.name
    handle.close()
    archive = _Archive(path)
    counts = {
        "vacancies": 0,
        "bookmarks": 0,
        "clicks": 0,
        "featured": 0,
        "requirements": 0,
        "reports": 0,
        "matches": 0,
        "applications": 0,
    }
    try:
        archive.field("generated_at", when.isoformat())
        archive.field(
            "rule",
            "closing day ended in Africa/Johannesburg, or the scanner marked the role closed or gone",
        )
        archive.start_array("vacancies")
        for chunk in _chunks(ids):
            rows = db.query(Vacancy).filter(Vacancy.id.in_(chunk)).all()
            counts["vacancies"] += _write_query(archive, rows)
            db.expire_all()
        archive.end_array(last=False)
        sections = (
            ("bookmarks", SavedOpportunity, SavedOpportunity.vacancy_id, "bookmarks"),
            ("clicks", UsageClickDaily, UsageClickDaily.target_id, "clicks"),
            ("featured", EmployerEntitlement, EmployerEntitlement.vacancy_id, "featured"),
            ("requirements", VacancyRequirement, VacancyRequirement.vacancy_id, "requirements"),
            ("reports", VacancyReport, VacancyReport.vacancy_id, "reports"),
            ("matches", CandidateMatch, CandidateMatch.vacancy_id, "matches"),
            ("applications", Application, Application.vacancy_id, "applications"),
        )
        for index, (name, model, column, count_key) in enumerate(sections):
            archive.start_array(name)
            for chunk in _chunks(ids):
                query = db.query(model).filter(column.in_(chunk))
                if model is UsageClickDaily:
                    query = query.filter(UsageClickDaily.target_kind == "vacancy")
                counts[count_key] += _write_query(archive, query.all())
                db.expire_all()
            archive.end_array(last=index == len(sections) - 1)
        payload = archive.close()
    finally:
        if os.path.exists(path):
            os.unlink(path)
    if counts["vacancies"] != len(ids):
        raise RuntimeError("Expired-opportunity backup did not include every selected row.")
    storage = get_storage()
    storage.put(key, payload)
    stored = storage.get(key)
    if stored != payload:
        raise RuntimeError("Expired-opportunity backup did not read back intact.")
    with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as gz:
        body = json.loads(gz.read().decode("utf-8"))
    if len(body.get("vacancies") or []) != len(ids):
        raise RuntimeError("Expired-opportunity backup did not list every selected row.")
    counts["backup"] = key
    return key, counts


def _still_due(db: Session, ids: list[str], today: date) -> list[str]:
    due = []
    clauses = due_for_deletion_clauses(today)
    for chunk in _chunks(ids):
        rows = db.query(Vacancy.id).filter(Vacancy.id.in_(chunk), *clauses).all()
        due.extend(row[0] for row in rows)
    return due


def _remember(db: Session, vacancies: list[Vacancy], board_urls: dict[str, str], when: datetime) -> None:
    for vacancy in vacancies:
        hashes = [public_id_hash(vacancy.id)]
        hashes.extend(identity_hashes(
            company_id=vacancy.company_id,
            external_id=vacancy.external_id,
            source_url=vacancy.source_url,
            canonical_url=vacancy.canonical_url,
            application_url=vacancy.application_url,
            fingerprint=vacancy.fingerprint,
            board_url=board_urls.get(vacancy.source_id),
        ))
        for digest in dict.fromkeys(hashes):
            if db.get(OpportunityTombstone, digest) is None:
                db.add(OpportunityTombstone(key_hash=digest, deleted_at=when))


def _delete(db: Session, ids: list[str], when: datetime) -> dict:
    """End featured placements, then remove dependent rows, then the vacancies."""
    ended = 0
    bookmarks = 0
    clicks = 0
    for chunk in _chunks(ids):
        featured = (
            db.query(EmployerEntitlement)
            .filter(EmployerEntitlement.vacancy_id.in_(chunk))
            .all()
        )
        for row in featured:
            ends_at = row.ends_at
            if ends_at is not None and ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
            still_running = ends_at is not None and ends_at > when
            if row.status == "active" or still_running:
                ended += 1
            if row.status == "active":
                row.status = "expired"
            if still_running:
                row.ends_at = when
        clicks += (
            db.query(UsageClickDaily)
            .filter(UsageClickDaily.target_kind == "vacancy", UsageClickDaily.target_id.in_(chunk))
            .delete(synchronize_session=False)
        )
        bookmarks += (
            db.query(SavedOpportunity)
            .filter(SavedOpportunity.vacancy_id.in_(chunk))
            .delete(synchronize_session=False)
        )
        db.query(EmployerOpportunity).filter(EmployerOpportunity.vacancy_id.in_(chunk)).update(
            {EmployerOpportunity.vacancy_id: None}, synchronize_session=False,
        )
        db.query(CVVersion).filter(CVVersion.vacancy_id.in_(chunk)).update(
            {CVVersion.vacancy_id: None}, synchronize_session=False,
        )
        db.query(CoverLetter).filter(CoverLetter.vacancy_id.in_(chunk)).update(
            {CoverLetter.vacancy_id: None}, synchronize_session=False,
        )
        db.query(InterviewPrep).filter(InterviewPrep.vacancy_id.in_(chunk)).update(
            {InterviewPrep.vacancy_id: None}, synchronize_session=False,
        )
        db.query(Vacancy).filter(Vacancy.duplicate_of_id.in_(chunk)).update(
            {Vacancy.duplicate_of_id: None}, synchronize_session=False,
        )
        application_ids = [
            row[0]
            for row in db.query(Application.id).filter(Application.vacancy_id.in_(chunk)).all()
        ]
        if application_ids:
            db.query(ApplicationAnswer).filter(ApplicationAnswer.application_id.in_(application_ids)).delete(
                synchronize_session=False,
            )
            db.query(ApplicationEvent).filter(ApplicationEvent.application_id.in_(application_ids)).delete(
                synchronize_session=False,
            )
            db.query(Application).filter(Application.id.in_(application_ids)).delete(synchronize_session=False)
        db.query(VacancyReport).filter(VacancyReport.vacancy_id.in_(chunk)).delete(synchronize_session=False)
        match_ids = [
            row[0]
            for row in db.query(CandidateMatch.id).filter(CandidateMatch.vacancy_id.in_(chunk)).all()
        ]
        if match_ids:
            db.query(CVVersion).filter(CVVersion.match_id.in_(match_ids)).update(
                {CVVersion.match_id: None}, synchronize_session=False,
            )
            db.query(CoverLetter).filter(CoverLetter.match_id.in_(match_ids)).update(
                {CoverLetter.match_id: None}, synchronize_session=False,
            )
            db.query(InterviewPrep).filter(InterviewPrep.match_id.in_(match_ids)).update(
                {InterviewPrep.match_id: None}, synchronize_session=False,
            )
        db.query(CandidateMatch).filter(CandidateMatch.vacancy_id.in_(chunk)).delete(synchronize_session=False)
        db.query(VacancyRequirement).filter(VacancyRequirement.vacancy_id.in_(chunk)).delete(
            synchronize_session=False,
        )
        vacancies = db.query(Vacancy).filter(Vacancy.id.in_(chunk)).all()
        source_ids = {row.source_id for row in vacancies}
        boards = {
            row.id: row.url
            for row in db.query(VacancySource.id, VacancySource.url).filter(VacancySource.id.in_(source_ids)).all()
        } if source_ids else {}
        _remember(db, vacancies, boards, when)
        db.flush()
        db.query(Vacancy).filter(Vacancy.id.in_(chunk)).delete(synchronize_session=False)
    return {"deleted": len(ids), "bookmarks": bookmarks, "clicks": clicks, "featured_ended": ended}


def purge_expired_opportunities(db: Session, when: datetime | None = None) -> dict:
    """Back up expired rows, then delete them. Returns counts and the backup key."""
    import os
    if os.getenv("OPPORTUNITY_PURGE_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        # Off unless the owner switches it on. Closed rows are already hidden
        # from every public page; deleting them is a separate decision.
        return {"deleted": 0, "backup": None, "bookmarks": 0, "clicks": 0,
                "featured_ended": 0, "disabled": True}
    moment = when or datetime.now(timezone.utc)
    today = sa_today(moment)
    selected = [row[0] for row in db.query(Vacancy.id).filter(*due_for_deletion_clauses(today)).all()]
    if not selected:
        return {
            "deleted": 0,
            "backup": None,
            "bookmarks": 0,
            "clicks": 0,
            "featured_ended": 0,
        }
    key, backed_up = _backup(db, selected, moment)
    due = _still_due(db, selected, today)
    if not due:
        db.add(AdminAuditLog(
            admin_id=_SYSTEM_ACTOR,
            action="purge_expired",
            target_user_id=None,
            detail=f"deleted=0 backup={key} reopened_before_delete={len(selected)}"[:500],
        ))
        db.commit()
        return {
            "deleted": 0,
            "backup": key,
            "bookmarks": 0,
            "clicks": 0,
            "featured_ended": 0,
        }
    removed = _delete(db, due, moment)
    detail = (
        f"deleted={removed['deleted']} backup={key} "
        f"bookmarks={removed['bookmarks']} clicks={removed['clicks']} "
        f"featured_ended={removed['featured_ended']}"
    )
    db.add(AdminAuditLog(
        admin_id=_SYSTEM_ACTOR,
        action="purge_expired",
        target_user_id=None,
        detail=detail[:500],
    ))
    db.commit()
    db.expire_all()
    return {"backup": key, **removed, "backed_up": backed_up["vacancies"]}
