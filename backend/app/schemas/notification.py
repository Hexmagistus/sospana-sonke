"""Schemas for notifications and scheduler admin."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
        if v is None or v == "":
            return None
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("link_url must start with http:// or https://")
        return v


class AdminSuggestionResponse(BaseModel):
    sent: int


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


class JobRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_name: str
    status: str
    detail: str | None
    started_at: datetime
    finished_at: datetime | None
