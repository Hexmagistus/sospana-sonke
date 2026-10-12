"""Saved daily-role alerts. Responses carry the filter only, never advert text."""
from pydantic import BaseModel, ConfigDict, Field


class RoleAlertWrite(BaseModel):
    country: str | None = Field(default=None, max_length=80)
    category: str | None = Field(default=None, max_length=40)
    keyword: str | None = Field(default=None, max_length=80)


class RoleAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    country: str | None
    category: str | None
    keyword: str | None
    active: bool


class AlertMatchResponse(BaseModel):
    title: str
    employer: str
    country: str
    url: str | None
    last_seen: str | None


class AlertPreviewResponse(BaseModel):
    email_sent: bool
    would_send: bool
    cadence: str
    window_hours: int
    digest_eligible: bool
    would_email: list[AlertMatchResponse]
    open_matches: list[AlertMatchResponse]
