"""Schemas for advertiser spot applications."""
import re
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MIN_USD_PER_DAY = Decimal("1.00")
MAX_USD_PER_DAY = Decimal("10000.00")
MAX_DAYS = 365
SLOTS_PER_SIDE = 10
SLOT_KEY = re.compile(r"^[LR](?:10|[1-9])$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def valid_slot_key(value: str) -> bool:
    return bool(SLOT_KEY.match(value))


def clean_text(value: str) -> str:
    """One line, no control characters, single spaces."""
    return " ".join(_CONTROL.sub(" ", value).split())


class AdApplicationCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    contact_email: EmailStr
    website: str = Field(min_length=4, max_length=500)
    ad_text: str = Field(min_length=3, max_length=120)
    amount_usd_per_day: Decimal = Field(max_digits=10, decimal_places=2)
    days: int = Field(ge=1, le=MAX_DAYS)
    requested_slot: str | None = Field(default=None, max_length=4)

    @field_validator("business_name", "ad_text")
    @classmethod
    def _one_line(cls, v: str) -> str:
        v = clean_text(v)
        if len(v) < 2:
            raise ValueError("Please fill this in.")
        return v

    @field_validator("amount_usd_per_day")
    @classmethod
    def _minimum(cls, v: Decimal) -> Decimal:
        if v < MIN_USD_PER_DAY:
            raise ValueError("The minimum is $1 per day.")
        if v > MAX_USD_PER_DAY:
            raise ValueError("That amount is too large. Please contact us instead.")
        return v

    @field_validator("website")
    @classmethod
    def _website(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^https?://", v, re.I):
            v = "https://" + v
        parsed = urlparse(v)
        host = parsed.hostname or ""
        if parsed.scheme not in ("http", "https") or "." not in host or " " in v or parsed.username or parsed.password:
            raise ValueError("Enter your website address, for example https://example.com")
        if len(v) > 500:
            raise ValueError("That web address is too long.")
        return v

    @field_validator("requested_slot")
    @classmethod
    def _slot(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if not valid_slot_key(v):
            raise ValueError("Unknown spot.")
        return v


class AdApplicationReceipt(BaseModel):
    id: str
    status: str
    total_usd: Decimal
    message: str


class PublicAd(BaseModel):
    slot_key: str
    business_name: str
    ad_text: str
    website: str


class AdApplicationAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    business_name: str
    contact_email: str
    website: str
    ad_text: str
    amount_usd_per_day: Decimal
    days: int
    requested_slot: str | None
    status: str
    slot_key: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    admin_note: str | None
    created_at: datetime


class AdDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected|pending)$")
    slot_key: str | None = Field(default=None, max_length=4)
    admin_note: str | None = Field(default=None, max_length=1000)
