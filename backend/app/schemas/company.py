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
    official_website: str | None = None
    active: bool
    scraping_status: str
    last_checked: datetime | None
    last_http_status: int | None
    url_looks_like_careers: bool | None
    automation_mode: str
    requires_login: bool
    has_captcha: bool
    notes: str | None
    # "Updated recently" signal from the lightweight page-hash checker (see
    # app/services/link_check_service.py) -- None until at least two checks
    # have found a difference. Most useful for careers links that are just a
    # homepage/news feed rather than a structured job board.
    content_changed_at: datetime | None = None


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


class CoverageRow(BaseModel):
    """One country/category cell of the coverage map (GET /companies/coverage)
    -- an honest rollup of how much of the directory is a verified working
    link vs. still pending verification vs. needing attention, doubling as
    the team's own to-do list for filling gaps."""
    country: str
    source_type: str
    total: int
    active: int
    with_careers_url: int
    verified_ok: int
    pending_verification: int
    needs_attention: int
