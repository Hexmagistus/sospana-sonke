"""Schemas for vacancies, requirements, sources, and scan reports."""
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class VacancyRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    text: str
    kind: str
    category: str
    extracted_by: str


class VacancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    external_id: str | None
    title: str
    department: str | None
    location: str | None
    work_mode: str | None
    employment_type: str | None
    salary: str | None
    province: str | None
    salary_min: int | None
    salary_max: int | None
    nqf_level: int | None
    trust_flags: list[str] | None
    duplicate_of_id: str | None
    posting_date: date | None
    closing_date: date | None
    application_url: str | None
    source_url: str | None
    canonical_url: str | None = None
    source_domain: str | None = None
    city: str | None = None
    country: str | None = None
    salary_currency: str | None = None
    lifecycle_status: str | None = None
    verification_state: str | None = None
    quality_score: int | None = None
    is_open: bool
    first_seen_at: datetime
    last_seen_at: datetime


class VacancyDetailResponse(VacancyResponse):
    description: str | None
    requirements: list[VacancyRequirementResponse]
    requirements_text: str | None = None
    qualifications: str | None = None
    experience: str | None = None


class VacancySourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    url: str
    ats_type: str
    active: bool
    robots_allowed: bool | None
    last_checked: datetime | None
    last_status: str
    consecutive_failures: int
    last_error: str | None
    last_vacancy_count: int | None
    scraper_status: str | None = None
    error_category: str | None = None
    duplicates_prevented: int = 0
    empty_streak: int = 0
    http_status: int | None = None
    parser_used: str | None = None


class VacancyReportCreate(BaseModel):
    category: str  # one of app.models.vacancy_report.VACANCY_REPORT_CATEGORIES
    details: str | None = None


class VacancyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    vacancy_id: str
    category: str
    details: str | None
    status: str
    created_at: datetime


class DuplicateGroupResponse(BaseModel):
    keep: VacancyResponse
    duplicates: list[VacancyResponse]


class MergeDuplicatesRequest(BaseModel):
    keep_id: str
    duplicate_ids: list[str]


class MergeDuplicatesResponse(BaseModel):
    merged: int


class ScanReportResponse(BaseModel):
    source_id: str
    status: str
    created: int = 0
    updated: int = 0
    closed: int = 0
    total_seen: int = 0
    duplicates_prevented: int = 0
    error: str | None = None
    warnings: list[str] = []
