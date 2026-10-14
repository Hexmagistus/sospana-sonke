"""Public listings stop when a role has closed.

A role is expired at the end of its closing day in South Africa, or when the
scanner has marked it closed or gone. ``status`` is ``active`` or ``expired``.
``expired_at`` is the first time that was recorded. Rows stay hidden until the
purge job has written a backup and deleted them.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.models.vacancy import Vacancy

SA_ZONE = ZoneInfo("Africa/Johannesburg")
STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"
# Scanner words that mean the listing is closed or no longer on the board.
_SCANNER_GONE = ("CLOSED", "EXPIRED", "REMOVED")
_STILL_OPEN = ("ACTIVE", "OPEN")


def sa_today(moment: datetime | None = None) -> date:
    """The calendar date in South Africa. The closing day itself is still open."""
    when = moment or datetime.now(SA_ZONE)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(SA_ZONE).date()


def closing_has_passed(closing: date | None, today: date | None = None) -> bool:
    """True after the end of the closing day in South Africa."""
    if closing is None:
        return False
    return closing < (today if today is not None else sa_today())


def scanner_marked_gone(vacancy: Vacancy) -> bool:
    if not vacancy.is_open:
        return True
    life = (vacancy.lifecycle_status or "").upper()
    return life in _SCANNER_GONE


def is_publicly_listed(vacancy: Vacancy, today: date | None = None) -> bool:
    """The same rule as ``public_role_clauses``, for one loaded row."""
    if vacancy.deleted_at is not None:
        return False
    if (getattr(vacancy, "status", None) or STATUS_ACTIVE) == STATUS_EXPIRED:
        return False
    if not vacancy.is_open:
        return False
    life = (vacancy.lifecycle_status or "ACTIVE").upper()
    if life not in _STILL_OPEN:
        return False
    if closing_has_passed(vacancy.closing_date, today):
        return False
    return True


def expired_role_clauses(today: date | None = None):
    """Rows kept in the database that must not appear on a public page."""
    day = today if today is not None else sa_today()
    return (
        Vacancy.deleted_at.is_(None),
        or_(
            Vacancy.status == STATUS_EXPIRED,
            Vacancy.is_open.is_(False),
            func.upper(func.coalesce(Vacancy.lifecycle_status, "")).in_(_SCANNER_GONE),
            and_(Vacancy.closing_date.isnot(None), Vacancy.closing_date < day),
        ),
    )


def due_for_deletion_clauses(today: date | None = None):
    """Expired rows, including ones already soft-deleted. The purge job uses this."""
    day = today if today is not None else sa_today()
    return (
        or_(
            Vacancy.status == STATUS_EXPIRED,
            Vacancy.is_open.is_(False),
            func.upper(func.coalesce(Vacancy.lifecycle_status, "")).in_(_SCANNER_GONE),
            and_(Vacancy.closing_date.isnot(None), Vacancy.closing_date < day),
        ),
    )


def public_role_clauses(today: date | None = None):
    """SQL filters for a role that may still be shown on a public page."""
    day = today if today is not None else sa_today()
    return (
        Vacancy.deleted_at.is_(None),
        or_(Vacancy.status.is_(None), Vacancy.status == STATUS_ACTIVE),
        Vacancy.is_open.is_(True),
        or_(Vacancy.lifecycle_status.is_(None), Vacancy.lifecycle_status.in_(_STILL_OPEN)),
        or_(Vacancy.closing_date.is_(None), Vacancy.closing_date >= day),
    )


def mark_expired(vacancy: Vacancy, when: datetime | None = None) -> None:
    """Record expiry. A scanner reason already stored on the row is kept."""
    moment = when or datetime.now(timezone.utc)
    if vacancy.expired_at is None:
        vacancy.expired_at = moment
    vacancy.status = STATUS_EXPIRED
    vacancy.is_open = False
    life = (vacancy.lifecycle_status or "").upper()
    if life not in _SCANNER_GONE:
        vacancy.lifecycle_status = "EXPIRED"


def mark_active(vacancy: Vacancy) -> None:
    """A role the scanner has seen again, and whose closing day has not ended."""
    vacancy.status = STATUS_ACTIVE
    vacancy.expired_at = None
    vacancy.is_open = True
    vacancy.lifecycle_status = "ACTIVE"


def stamp_expired(db: Session, when: datetime | None = None) -> int:
    """Set status and expired_at on rows that are already closed. No deletes.

    Returns how many open rows were closed because the closing day has ended.
    Rows the scanner had already closed are stamped too, and are not in that count.
    The update stays in the database so a large directory is not loaded into memory.
    """
    moment = when or datetime.now(timezone.utc)
    today = sa_today(moment)
    not_stamped = or_(Vacancy.status.is_(None), Vacancy.status != STATUS_EXPIRED)
    values = {
        Vacancy.status: STATUS_EXPIRED,
        Vacancy.is_open: False,
        Vacancy.expired_at: func.coalesce(Vacancy.expired_at, moment),
        Vacancy.lifecycle_status: case(
            (func.upper(func.coalesce(Vacancy.lifecycle_status, "")).in_(_SCANNER_GONE), Vacancy.lifecycle_status),
            else_="EXPIRED",
        ),
    }
    date_due = and_(
        Vacancy.deleted_at.is_(None),
        not_stamped,
        Vacancy.is_open.is_(True),
        Vacancy.closing_date.isnot(None),
        Vacancy.closing_date < today,
    )
    closed_count = int(db.query(func.count(Vacancy.id)).filter(date_due).scalar() or 0)
    if closed_count:
        db.query(Vacancy).filter(date_due).update(values, synchronize_session=False)
    scanner_gone = and_(
        Vacancy.deleted_at.is_(None),
        not_stamped,
        or_(
            Vacancy.is_open.is_(False),
            func.upper(func.coalesce(Vacancy.lifecycle_status, "")).in_(_SCANNER_GONE),
        ),
    )
    stamped_gone = db.query(Vacancy).filter(scanner_gone).update(values, synchronize_session=False)
    if closed_count or stamped_gone:
        db.commit()
    db.expire_all()
    return closed_count
