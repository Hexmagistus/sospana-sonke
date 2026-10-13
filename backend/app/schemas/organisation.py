"""Organisation accounts, plan prices, and employer posts."""
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class OrganisationRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    accepted_policy: bool = False


class ClaimRequest(BaseModel):
    company_id: str = Field(min_length=1, max_length=36)
    work_email: EmailStr
    note: str | None = Field(default=None, max_length=500)


class VerifyClaimRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class PageUpdateRequest(BaseModel):
    public_blurb: str | None = Field(default=None, max_length=2000)
    contact_email: EmailStr | None = None
    brand_headline: str | None = Field(default=None, max_length=160)


class CorrectionRequest(BaseModel):
    field_name: str = Field(min_length=1, max_length=40)
    proposed_value: str = Field(min_length=8, max_length=500)


class OpportunityWriteRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    opportunity_type: str = "job"
    location: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=20, max_length=8000)
    application_url: str = Field(min_length=8, max_length=1000)
    closing_date: date | None = None
    field_of_study: str | None = Field(default=None, max_length=400)
    stipend_text: str | None = Field(default=None, max_length=240)


class OpportunityPatchRequest(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    application_url: str | None = Field(default=None, max_length=1000)


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=20)
    opportunity_id: str | None = Field(default=None, max_length=36)


class ModerationRequest(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)


class PlanPriceUpdate(BaseModel):
    amount_zar: int | None = Field(default=None, ge=0, le=1_000_000)
    published: bool | None = None
    post_limit: int | None = Field(default=None, ge=0, le=500)
    duration_days: int | None = Field(default=None, ge=1, le=366)
    clear_amount: bool = False


class AccountResponse(BaseModel):
    id: str
    company_id: str
    status: str
    method: str | None = None
    work_email: str
    verified_at: datetime | None = None
    public_blurb: str | None = None
    contact_email: str | None = None
    brand_headline: str | None = None
    verification_token: str | None = None
