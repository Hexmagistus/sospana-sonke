"""Schemas for the "Tailor my CV to a job" pipeline: job analysis, match
report, fact-check, CV quality, application readiness, and the job
application tracker."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeJobRequest(BaseModel):
    job_title: str | None = None
    company_name: str | None = None
    job_description: str = Field(min_length=1)


class RequirementMatch(BaseModel):
    text: str
    note: str


class JobAnalysisResponse(BaseModel):
    """Summary shape — used for the application-tracker list view."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_title: str
    company_name: str | None
    match_score: float
    band: str
    decision: str
    ats_score: float | None
    quality_score: float | None
    readiness_score: float | None
    readiness_label: str | None
    template: str
    status: str
    date_applied: date | None
    cv_version_id: str | None
    cover_letter_id: str | None
    created_at: datetime


class JobAnalysisDetailResponse(JobAnalysisResponse):
    job_description: str
    extracted: dict
    sub_scores: dict
    confidence: str
    hard_ok: bool
    strong_matches: list[RequirementMatch]
    partial_matches: list[RequirementMatch]
    missing_requirements: list[RequirementMatch]
    ats_breakdown: dict | None
    quality_breakdown: dict | None
    quality_suggestions: list[str] | None
    recommended_action: str | None
    notes: str | None


class FactCheck(BaseModel):
    ok: bool
    violations: list[str]


class AnalyzeJobResult(BaseModel):
    job_analysis: JobAnalysisDetailResponse
    draft_cv: dict
    fact_check: FactCheck


class GenerateCvRequest(BaseModel):
    cv_data: dict
    template: str | None = None


class TrackerUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    date_applied: date | None = None


class TemplateInfo(BaseModel):
    id: str
    label: str
    description: str
