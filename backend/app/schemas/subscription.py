"""Schemas for subscription status and checkout."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    has_access: bool
    provider: str
    amount_zar: int
    currency: str
    trial_end: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool


class CheckoutResponse(BaseModel):
    authorization_url: str
    reference: str
