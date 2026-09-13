"""Schema for the (now purely historical) subscription status endpoint --
checkout/cancel/mock-pay were removed along with subscriptions themselves;
see app/api/routes_subscription.py."""
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
