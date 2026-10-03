"""Schemas for notifications and scheduler admin."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.notifications.links import validated_notice_url


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    title: str
    body: str
    related_type: str | None
    related_id: str | None
    link_url: str | None = None
    is_read: bool
    email_sent: bool
    sms_sent: bool
    push_sent: bool
    created_at: datetime


class AdminSuggestionRequest(BaseModel):
    """Admin-curated post/link, pushed to registered candidates the admin
    judges relevant -- delivered as a normal dashboard notification, so it
    shows up wherever notifications already do (Nav badge, Notifications page)."""
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=2000)
    link_url: str | None = Field(default=None, max_length=2000)
    # Specific candidates to target. Ignored (and may be omitted) when
    # all_candidates is true.
    user_ids: list[str] = Field(default_factory=list)
    # Broadcast to every active candidate instead of a hand-picked list.
    all_candidates: bool = False

    @field_validator("link_url")
    @classmethod
    def _http_or_none(cls, v: str | None) -> str | None:
        return validated_notice_url(v)


class AdminSuggestionResponse(BaseModel):
    sent: int
    skipped: int = 0
    # Same person and the same link already had a notice. Nothing new was stored or mailed.
    duplicates: int = 0


class UnreadCountResponse(BaseModel):
    unread: int


class PushTokenRequest(BaseModel):
    token: str
    platform: str = "web"


class PushTokenResponse(BaseModel):
    id: str
    platform: str


class ScheduleResponse(BaseModel):
    schedule: dict


class ScheduleUpdateRequest(BaseModel):
    schedule: dict


class SourceHealthItem(BaseModel):
    source_id: str | None = None
    company_id: str | None = None
    company_name: str
    country: str | None = None
    ats_type: str
    url: str
    active: bool = True
    last_status: str
    scraper_status: str | None = None
    last_error: str | None = None
    last_checked: datetime | None = None
    last_vacancy_count: int | None = None
    consecutive_failures: int = 0


class SourceHealthResponse(BaseModel):
    """Per-source scan health for the admin dashboard."""
    sources: int
    employers: int = 0
    open_vacancies: int
    expired_vacancies: int = 0
    vacancies_new_today: int = 0
    vacancies_new_week: int = 0
    duplicates_prevented: int = 0
    needs_review: int = 0
    last_success_at: datetime | None = None
    by_status: dict[str, int]
    by_scraper_status: dict[str, int] = {}
    by_ats: dict[str, int]
    recent: list[SourceHealthItem]


class ScanLogItem(BaseModel):
    id: str
    company_id: str
    company_name: str | None = None
    url: str | None = None
    status: str
    error_category: str | None = None
    pages_scanned: int = 0
    vacancies_discovered: int = 0
    vacancies_new: int = 0
    vacancies_updated: int = 0
    duplicates_prevented: int = 0
    vacancies_closed: int = 0
    duration_ms: int | None = None
    parser_used: str | None = None
    finished_at: datetime | None = None


class SourceActiveUpdate(BaseModel):
    active: bool


class JobRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_name: str
    status: str
    detail: str | None
    started_at: datetime
    finished_at: datetime | None
