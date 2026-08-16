"""Schemas for dashboards and reports."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CandidateDashboardResponse(BaseModel):
    subscription_status: str
    has_access: bool
    plan_amount_zar: int
    vacancies_open: int
    total_matches: int
    strong_matches: int
    apply_matches: int
    cvs_generated: int
    cover_letters_generated: int
    applications_total: int
    applications_submitted: int
    applications_awaiting_action: int
    interviews: int
    offers: int


class AdminDashboardResponse(BaseModel):
    registered_candidates: int
    active_subscriptions: int
    paying_subscriptions: int
    estimated_mrr_zar: int
    companies_total: int
    companies_active: int
    sources_failing: int
    vacancies_open: int
    vacancies_total: int
    applications_total: int
    applications_by_status: dict
    cv_versions_total: int


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    label: str
    stats: dict
    created_at: datetime
