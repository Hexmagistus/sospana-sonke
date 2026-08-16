"""Schemas for generated CV versions and cover letters."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CVVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    match_id: str | None
    vacancy_id: str | None
    label: str
    template: str
    ats_score: float | None
    ats_breakdown: dict | None
    truthfulness_ok: bool
    truthfulness_violations: list | None
    generated_by: str
    created_at: datetime


class CoverLetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    match_id: str | None
    vacancy_id: str | None
    label: str
    body: str
    truthfulness_ok: bool
    generated_by: str
    created_at: datetime
