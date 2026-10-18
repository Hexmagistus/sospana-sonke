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
click totals and other rows that reference the vacancy, write tombstones,
then delete the vacancies. A backup that does not read back stops the run
with every row still in place.

Safety rules:

- A listing that any user has applied to or bookmarked is never deleted. It
  stays hidden by the public listing rule. Its applications, answers, events
  and bookmarks are untouched.
- Every row the delete removes or changes is in the archive first. That
  includes rows a database cascade or SET NULL would reach.
  ``BACKED_UP_TABLES`` names them, and a test fails if a foreign key reaches a
  table that is not on that list.
- One run handles at most ``OPPORTUNITY_PURGE_BATCH`` listings (default
  1,000). The rest wait for the next run, so the archive stays small enough
  for a 512 MB server.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import tempfile
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import exists, func, insert, not_, or_
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
from app.services.opportunity_tombstone import identity_hashes, public_id_hash, url_hash
from app.services.storage import get_storage

# Cron has no signed-in administrator. The audit column is a 36-character id.
_SYSTEM_ACTOR = "00000000-0000-0000-0000-000000000000"
_CHUNK = 200
DEFAULT_BATCH = 1000
MAX_BATCH = 5000

# Every table the delete removes rows from or changes. Each one is in the archive.
BACKED_UP_TABLES = frozenset({
    "vacancies",               # deleted, and duplicate_of_id cleared on others
    "vacancy_requirements",    # deleted (cascade)
    "vacancy_reports",         # deleted (cascade)
    "candidate_matches",       # deleted (cascade)
    "saved_opportunities",     # never touched: bookmarked listings are kept
    "applications",            # never deleted; match_id may be cleared
    "application_answers",     # never touched: applied-to listings are kept
    "application_events",      # never touched: applied-to listings are kept
    "usage_click_daily",       # deleted (no foreign key)
    "employer_entitlements",   # featured placement ended (no foreign key)
    "employer_opportunities",  # vacancy_id cleared (no foreign key)
    "cv_versions",             # vacancy_id / match_id cleared
    "cover_letters",           # vacancy_id / match_id cleared
    "interview_preps",         # vacancy_id / match_id cleared
})


def batch_size() -> int:
    raw = os.getenv("OPPORTUNITY_PURGE_BATCH", "").strip()
    try:
        value = int(raw) if raw else DEFAULT_BATCH
    except ValueError:
        value = DEFAULT_BATCH
    return max(1, min(value, MAX_BATCH))


def has_user_records():
    """SQL clause: someone applied to or bookmarked this listing."""
    return or_(
        exists().where(Application.vacancy_id == Vacancy.id),
        exists().where(SavedOpportunity.vacancy_id == Vacancy.id),
    )


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


def _match_ids(db: Session, ids: list[str]) -> list[str]:
    found = []
    for chunk in _chunks(ids):
        found.extend(row[0] for row in db.query(CandidateMatch.id).filter(CandidateMatch.vacancy_id.in_(chunk)).all())
    return found


def _sections():
    """(archive name, model, column matched to listing ids, column matched to match ids).

    Every table the delete removes rows from or changes is here.
    Answers and events are selected through the archived applications.
    """
    return (
        ("bookmarks", SavedOpportunity, SavedOpportunity.vacancy_id, None),
        ("clicks", UsageClickDaily, UsageClickDaily.target_id, None),
        ("featured", EmployerEntitlement, EmployerEntitlement.vacancy_id, None),
        ("employer_opportunities", EmployerOpportunity, EmployerOpportunity.vacancy_id, None),
        ("requirements", VacancyRequirement, VacancyRequirement.vacancy_id, None),
        ("reports", VacancyReport, VacancyReport.vacancy_id, None),
        ("matches", CandidateMatch, CandidateMatch.vacancy_id, None),
        ("duplicates", Vacancy, Vacancy.duplicate_of_id, None),
        ("applications", Application, Application.vacancy_id, Application.match_id),
        ("application_answers", ApplicationAnswer, None, None),
        ("application_events", ApplicationEvent, None, None),
        ("cv_versions", CVVersion, CVVersion.vacancy_id, CVVersion.match_id),
        ("cover_letters", CoverLetter, CoverLetter.vacancy_id, CoverLetter.match_id),
        ("interview_preps", InterviewPrep, InterviewPrep.vacancy_id, InterviewPrep.match_id),
    )


def _section_rows(db: Session, model, vac_col, match_col, ids, match_ids, application_ids):
    """Yield each row once, chunk by chunk, so memory stays flat."""
    if model in (ApplicationAnswer, ApplicationEvent):
        passes = [(model.application_id, application_ids)]
    else:
        passes = [(vac_col, ids)]
        if match_col is not None:
            passes.append((match_col, match_ids))
    seen: set = set()
    for column, values in passes:
        for chunk in _chunks(values):
            query = db.query(model).filter(column.in_(chunk))
            if model is UsageClickDaily:
                query = query.filter(UsageClickDaily.target_kind == "vacancy")
            for row in query.all():
                identity = tuple(getattr(row, c.name) for c in model.__table__.primary_key.columns)
                if identity in seen:
                    continue
                seen.add(identity)
                yield row
            db.expire_all()


def _backup(db: Session, ids: list[str], when: datetime) -> tuple[str, dict]:
    stamp = when.strftime("%Y%m%dT%H%M%SZ")
    # A random suffix keeps every run's key unique, so a backup left by a run
    # that rolled back is never reused or overwritten by the next run.
    key = f"private/expired-opportunities/{stamp}-{len(ids)}-{uuid.uuid4().hex[:8]}.json.gz"
    handle = tempfile.NamedTemporaryFile(prefix="expired-opportunities-", suffix=".json.gz", delete=False)
    path = handle.name
    handle.close()
    archive = _Archive(path)
    match_ids = _match_ids(db, ids)
    sections = _sections()
    counts = {"vacancies": 0, **{name: 0 for name, *_rest in sections}}
    application_ids: list[str] = []
    try:
        archive.field("generated_at", when.isoformat())
        archive.field(
            "rule",
            "closing day ended in Africa/Johannesburg, or the scanner marked the role closed or gone; "
            "listings with an application or bookmark are kept",
        )
        archive.start_array("vacancies")
        for chunk in _chunks(ids):
            rows = db.query(Vacancy).filter(Vacancy.id.in_(chunk)).all()
            counts["vacancies"] += _write_query(archive, rows)
            db.expire_all()
        archive.end_array(last=False)
        for index, (name, model, vac_col, match_col) in enumerate(sections):
            archive.start_array(name)
            for row in _section_rows(db, model, vac_col, match_col, ids, match_ids, application_ids):
                archive.item(_plain(row))
                counts[name] += 1
                if model is Application:
                    application_ids.append(row.id)
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
    del body, stored, payload
    counts["backup"] = key
    return key, counts


def _still_due(db: Session, ids: list[str], today: date) -> list[str]:
    due = []
    clauses = due_for_deletion_clauses(today)
    for chunk in _chunks(ids):
        rows = db.query(Vacancy.id).filter(Vacancy.id.in_(chunk), *clauses, not_(has_user_records())).all()
        due.extend(row[0] for row in rows)
    return due


def _url_columns(vacancy, board: str) -> list[str]:
    found = []
    for url in (vacancy.canonical_url, vacancy.application_url, vacancy.source_url):
        cleaned = (url or "").strip()
        if cleaned and cleaned != board and cleaned not in found:
            found.append(cleaned)
    return found


def _shared_url_hashes(db: Session, vacancies: list[Vacancy], board_urls: dict[str, str]) -> set[str]:
    """URL hashes that more than one listing of the same employer uses.

    Such an address is a general careers or search page, not one role's own
    address. A tombstone on it would block every future role from that
    employer that links to the same page, so it is left out. The role's id,
    employer reference and fingerprint hashes are still written.
    """
    users: dict[tuple[str, str], set[str]] = {}
    wanted: set[str] = set()
    for vacancy in vacancies:
        for url in _url_columns(vacancy, (board_urls.get(vacancy.source_id) or "").strip()):
            users.setdefault((vacancy.company_id, url), set()).add(vacancy.id)
            wanted.add(url)
    urls = sorted(wanted)
    for chunk in _chunks(urls):
        for column in (Vacancy.canonical_url, Vacancy.application_url, Vacancy.source_url):
            for vacancy_id, company_id, value in (
                db.query(Vacancy.id, Vacancy.company_id, column).filter(column.in_(chunk)).all()
            ):
                key = (company_id, (value or "").strip())
                if key in users:
                    users[key].add(vacancy_id)
    return {url_hash(company_id, url) for (company_id, url), ids in users.items() if len(ids) > 1}


def _insert_tombstones(db: Session, digests: list[str], when: datetime) -> int:
    """Insert new tombstones. One that already exists is left as it is."""
    written = 0
    dialect = db.get_bind().dialect.name
    for chunk in _chunks(digests):
        rows = [{"key_hash": digest, "deleted_at": when} for digest in chunk]
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as dialect_insert
        elif dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as dialect_insert
        else:
            dialect_insert = None
        if dialect_insert is not None:
            stmt = dialect_insert(OpportunityTombstone).values(rows).on_conflict_do_nothing(
                index_elements=["key_hash"],
            )
            result = db.execute(stmt)
            written += max(result.rowcount or 0, 0)
            continue
        present = {
            row[0]
            for row in db.query(OpportunityTombstone.key_hash).filter(OpportunityTombstone.key_hash.in_(chunk)).all()
        }
        fresh = [row for row in rows if row["key_hash"] not in present]
        if fresh:
            db.execute(insert(OpportunityTombstone), fresh)
            written += len(fresh)
    return written


def _remember(
    db: Session, vacancies: list[Vacancy], board_urls: dict[str, str], when: datetime, seen: set[str],
) -> int:
    """Write each tombstone hash once per batch; existing ones are kept.

    Several listings in one batch can share a hash (the same address or
    fingerprint). ``seen`` holds every hash already sent in this batch, so
    the insert never carries the same key twice.
    """
    shared = _shared_url_hashes(db, vacancies, board_urls)
    digests: list[str] = []
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
        for digest in hashes:
            if digest in seen or digest in shared:
                continue
            seen.add(digest)
            digests.append(digest)
    return _insert_tombstones(db, digests, when)


def _delete(db: Session, ids: list[str], when: datetime) -> dict:
    """End featured placements, then remove dependent rows, then the vacancies."""
    ended = 0
    bookmarks = 0
    clicks = 0
    tombstones = 0
    seen: set[str] = set()
    # Never delete a listing someone applied to or bookmarked. The selection
    # already leaves them out; check every chunk before the first change.
    for chunk in _chunks(ids):
        if db.query(Application.id).filter(Application.vacancy_id.in_(chunk)).first() is not None:
            raise RuntimeError("Purge selected a listing with an application; nothing was deleted.")
        if db.query(SavedOpportunity.id).filter(SavedOpportunity.vacancy_id.in_(chunk)).first() is not None:
            raise RuntimeError("Purge selected a bookmarked listing; nothing was deleted.")
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
            db.query(Application).filter(Application.match_id.in_(match_ids)).update(
                {Application.match_id: None}, synchronize_session=False,
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
        tombstones += _remember(db, vacancies, boards, when, seen)
        db.flush()
        db.query(Vacancy).filter(Vacancy.id.in_(chunk)).delete(synchronize_session=False)
    return {
        "deleted": len(ids), "bookmarks": bookmarks, "clicks": clicks, "featured_ended": ended,
        "tombstones": tombstones,
    }


def _empty(**extra) -> dict:
    return {
        "deleted": 0, "backup": None, "bookmarks": 0, "clicks": 0, "featured_ended": 0, "tombstones": 0,
        **extra,
    }


def purge_counts(db: Session, today: date) -> dict:
    """How many expired listings are waiting, and how many are kept for users."""
    due = db.query(func.count(Vacancy.id)).filter(*due_for_deletion_clauses(today))
    kept = int(due.filter(has_user_records()).scalar() or 0)
    total = int(due.scalar() or 0)
    return {"due": total - kept, "kept_for_users": kept}


def purge_expired_opportunities(db: Session, when: datetime | None = None, limit: int | None = None) -> dict:
    """Back up one batch of expired rows, then delete them.

    Listings with an application or a bookmark are skipped. Returns counts,
    the backup key and how many deletable listings are still waiting.
    """
    if os.getenv("OPPORTUNITY_PURGE_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        # Off unless the owner switches it on. Closed rows are already hidden
        # from every public page; deleting them is a separate decision.
        return _empty(disabled=True)
    moment = when or datetime.now(timezone.utc)
    today = sa_today(moment)
    size = max(1, min(limit, MAX_BATCH)) if limit else batch_size()
    selected = [
        row[0]
        for row in db.query(Vacancy.id)
        .filter(*due_for_deletion_clauses(today), not_(has_user_records()))
        .order_by(Vacancy.id)
        .limit(size)
        .all()
    ]
    if not selected:
        return _empty(**purge_counts(db, today), batch_limit=size)
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
        return {**_empty(), "backup": key, **purge_counts(db, today), "batch_limit": size}
    removed = _delete(db, due, moment)
    detail = (
        f"deleted={removed['deleted']} backup={key} "
        f"bookmarks={removed['bookmarks']} clicks={removed['clicks']} "
        f"featured_ended={removed['featured_ended']} matches={backed_up['matches']} "
        f"tombstones={removed['tombstones']}"
    )
    db.add(AdminAuditLog(
        admin_id=_SYSTEM_ACTOR,
        action="purge_expired",
        target_user_id=None,
        detail=detail[:500],
    ))
    db.commit()
    db.expire_all()
    left = purge_counts(db, today)
    return {
        "backup": key,
        **removed,
        "backed_up": backed_up["vacancies"],
        "matches_backed_up": backed_up["matches"],
        "batch_limit": size,
        "remaining": left["due"],
        "kept_for_users": left["kept_for_users"],
    }
