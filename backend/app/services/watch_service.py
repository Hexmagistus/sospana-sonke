"""Notify-me subscription service (company/country/category alerts).

A CompanyWatch lets a signed-in candidate opt into an alert when a careers
page changes -- either one specific company, or every company in a country
and/or source_type category. Matching is a simple, explainable rule (see
`matches`) rather than anything fuzzy, so a candidate always understands why
they got an email. See app/services/link_check_service.py for what triggers
the alert.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.watch import CompanyWatch


def create_watch(db: Session, *, user_id: str, company_id: str | None,
                 country: str | None, source_type: str | None) -> CompanyWatch:
    country = country.strip() or None if country else None
    source_type = source_type.strip().upper() or None if source_type else None

    if not company_id and not country and not source_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Choose a company, a country, or a category to watch.")
    if company_id and (db.get(Company, company_id) is None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    # Re-subscribing to the same scope reactivates it rather than creating a
    # duplicate row that would otherwise double-email the candidate later.
    existing = (db.query(CompanyWatch)
               .filter(CompanyWatch.user_id == user_id, CompanyWatch.company_id == company_id,
                       CompanyWatch.country == country, CompanyWatch.source_type == source_type)
               .first())
    if existing:
        existing.active = True
        db.commit()
        db.refresh(existing)
        return existing

    watch = CompanyWatch(user_id=user_id, company_id=company_id, country=country, source_type=source_type)
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


def delete_watch(db: Session, *, user_id: str, watch_id: str) -> None:
    watch = db.get(CompanyWatch, watch_id)
    if watch is None or watch.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch not found.")
    db.delete(watch)
    db.commit()


def matches(watch: CompanyWatch, company: Company) -> bool:
    """Does this watch cover this company? A company-scoped watch matches only
    that company; otherwise every set dimension (country, category) must
    agree -- an unset dimension on the watch means "any"."""
    if watch.company_id:
        return watch.company_id == company.id
    if watch.country and watch.country != company.country:
        return False
    if watch.source_type and watch.source_type != (company.source_type or "").upper():
        return False
    return True


def find_watchers_for_company(db: Session, company: Company) -> list[CompanyWatch]:
    """Every active watch whose scope covers this company. Loads all active
    watches and filters in Python -- simplest correct approach at the scale
    this table will realistically reach (candidates opting into alerts, not a
    bulk-imported dataset like companies), and avoids a fragile OR-with-NULL
    SQL expression across three optional dimensions."""
    return [w for w in db.query(CompanyWatch).filter(CompanyWatch.active.is_(True)).all()
            if matches(w, company)]
