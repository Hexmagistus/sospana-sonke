"""Crowd-sourced "report this opportunity" (see link_report_service.py for the
sibling company-link version, and trust_service.py for the automated signals
this complements)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.vacancy import Vacancy
from app.models.vacancy_report import VacancyReport, VACANCY_REPORT_CATEGORIES


def create_vacancy_report(db: Session, *, user_id: str, vacancy_id: str,
                          category: str, details: str | None) -> VacancyReport:
    vac = db.get(Vacancy, vacancy_id)
    if vac is None or vac.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found.")
    if category not in VACANCY_REPORT_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"category must be one of {VACANCY_REPORT_CATEGORIES}.",
        )
    report = VacancyReport(vacancy_id=vacancy_id, user_id=user_id, category=category,
                           details=(details or "").strip() or None)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
