"""Open-vacancy counts for the employer directory.

One grouped query for a page of companies. The number is how many vacancy
rows we currently hold, not an estimate of what the careers site lists.
"""
from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.vacancy import Vacancy

# Rows written by the scanner use ACTIVE. Older rows leave lifecycle_status
# null and rely on is_open. OPEN is included so a row that uses that word
# is still counted. CLOSED, EXPIRED, REMOVED, and UNKNOWN are not.
_OPEN_LIFECYCLE = ("ACTIVE", "OPEN")


def open_vacancy_counts(db: Session, company_ids: list[str]) -> dict[str, int]:
    """Count open, non-deleted vacancies per company. Missing ids mean zero."""
    if not company_ids:
        return {}
    rows = (
        db.query(Vacancy.company_id, func.count(Vacancy.id))
        .filter(
            Vacancy.company_id.in_(company_ids),
            Vacancy.is_open.is_(True),
            Vacancy.deleted_at.is_(None),
            or_(
                Vacancy.lifecycle_status.is_(None),
                Vacancy.lifecycle_status.in_(_OPEN_LIFECYCLE),
            ),
        )
        .group_by(Vacancy.company_id)
        .all()
    )
    return {company_id: int(n) for company_id, n in rows}
