"""Schemas for crowd-sourced broken-link reports."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LinkReportCreateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class LinkReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    reason: str
    status: str
    created_at: datetime
