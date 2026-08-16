"""Schemas for notifications and scheduler admin."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    title: str
    body: str
    related_type: str | None
    related_id: str | None
    is_read: bool
    email_sent: bool
    sms_sent: bool
    push_sent: bool
    created_at: datetime


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
