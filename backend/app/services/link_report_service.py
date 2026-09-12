"""Crowd-sourced broken-link reporting (see watch_service.py for alerts)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.link_report import LinkReport


def create_link_report(db: Session, *, user_id: str, company_id: str, reason: str) -> LinkReport:
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")
    report = LinkReport(company_id=company_id, user_id=user_id, reason=reason.strip())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
