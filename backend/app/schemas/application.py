"""Schemas for application settings, applications, answers, and events."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SettingsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    application_mode: str = Field(default="approval", pattern="^(automatic|approval|assisted)$")
    auto_apply_enabled: bool = False
    min_match_score: float = Field(default=70.0, ge=0, le=100)
    max_applications_per_day: int = Field(default=5, ge=0, le=100)
    max_applications_per_week: int = Field(default=25, ge=0, le=500)
    excluded_companies: list[str] = []
    excluded_roles: list[str] = []


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    question: str
    answer: str | None
    source: str
    is_unknown: bool


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_type: str
    status_from: str | None
    status_to: str | None
    detail: str | None
    actor: str
    created_at: datetime


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    vacancy_id: str
    match_id: str | None
    cv_version_id: str | None
    cover_letter_id: str | None
    mode: str
    status: str
    submission_method: str | None
    application_url: str | None
    action_required_note: str | None
    submitted_at: datetime | None
    authorised_at: datetime | None
    created_at: datetime


class ApplicationDetailResponse(ApplicationResponse):
    answers: list[AnswerResponse]
    events: list[EventResponse]


class StatusUpdateRequest(BaseModel):
    status: str


class AnswerUpdateRequest(BaseModel):
    value: str
