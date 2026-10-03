"""Open-vacancy counts for the employer directory.

One grouped query for a page of companies. The number is how many vacancy
rows we currently hold, not an estimate of what the careers site lists.
"""
from __future__ import annotations

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.vacancy import Vacancy, VacancySource

# Rows written by the scanner use ACTIVE. Older rows leave lifecycle_status
# null and rely on is_open. OPEN is included so a row that uses that word
# is still counted. CLOSED, EXPIRED, REMOVED, and UNKNOWN are not.
_OPEN_LIFECYCLE = ("ACTIVE", "OPEN")

# A structured parser that returned a list has counted the board. An empty
# static or JS read has not: the heuristic often misses a script-loaded list.
_STRUCTURED_PARSERS = (
    "greenhouse", "lever", "smartrecruiters", "recruitee", "workable",
    "workday", "oracle", "breezy", "pinpoint", "cihr",
    "cornerstone", "mci", "peoplesoft", "simplify",
)


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


def companies_with_known_vacancy_count(db: Session, company_ids: list[str]) -> set[str]:
    """Employers whose last structured read finished, including a real zero.

    ``SUCCESS`` means the parser returned roles. ``NO_VACANCIES`` counts only
    when that parser is structured. A static empty page still leaves the
    employer unknown. Holding open rows is applied by the caller, because
    those rows are a count even when this set is empty.
    """
    if not company_ids:
        return set()
    rows = (
        db.query(VacancySource.company_id)
        .filter(
            VacancySource.company_id.in_(company_ids),
            VacancySource.last_success_at.isnot(None),
            or_(
                VacancySource.scraper_status == "SUCCESS",
                and_(
                    VacancySource.scraper_status == "NO_VACANCIES",
                    VacancySource.parser_used.in_(_STRUCTURED_PARSERS),
                ),
            ),
        )
        .distinct()
        .all()
    )
    return {company_id for (company_id,) in rows}
