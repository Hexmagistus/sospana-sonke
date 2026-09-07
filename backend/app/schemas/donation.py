"""Schemas for the donation checkout flow."""
from pydantic import BaseModel, EmailStr, Field


class DonationCheckoutRequest(BaseModel):
    amount_zar: int = Field(gt=0)
    email: EmailStr
    name: str | None = Field(default=None, max_length=120)
    message: str | None = Field(default=None, max_length=500)


class DonationCheckoutResponse(BaseModel):
    authorization_url: str
    reference: str
