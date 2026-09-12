"""Schemas for notify-me (company/country/category) watch subscriptions."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WatchCreateRequest(BaseModel):
    # At least one of the three should be set (enforced in the service, not
    # here, so the error message can explain the "why" to the caller).
    company_id: str | None = None
    country: str | None = None
    source_type: str | None = None


class WatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str | None
    country: str | None
    source_type: str | None
    active: bool
    created_at: datetime
