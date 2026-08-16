"""Request/response schemas for companies and the URL tester."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_name: str
    jse_code: str | None
    source_type: str
    country: str
    careers_url: str | None
    active: bool
    scraping_status: str
    last_checked: datetime | None
    last_http_status: int | None
    url_looks_like_careers: bool | None
    automation_mode: str
    requires_login: bool
    has_captcha: bool
    notes: str | None


class CompanyImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    total_rows: int
    errors: list[str]


class AutomationPolicyRequest(BaseModel):
    automation_mode: str = Field(pattern="^(auto|assisted|manual|disabled)$")
    requires_login: bool = False
    has_captcha: bool = False


class UrlTestResult(BaseModel):
    url: str
    ok: bool
    status_code: int | None
    final_url: str | None
    looks_like_careers: bool
    error: str | None = None
