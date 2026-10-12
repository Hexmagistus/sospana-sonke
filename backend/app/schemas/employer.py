"""Public employer pages. Careers-link rows only. No research notes."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.vacancy import PublicJobResponse


class PublicEmployerSummary(BaseModel):
    id: str
    company_name: str
    country: str
    source_type: str


class PublicEmployerListResponse(BaseModel):
    employers: list[PublicEmployerSummary]
    matched: int
    limit: int
    offset: int


class PublicEmployerResponse(BaseModel):
    id: str
    company_name: str
    country: str
    source_type: str
    careers_url: str
    # "global" when the stored note says careers_scope=global. Otherwise null.
    # The note itself is not returned.
    careers_scope: str | None = None
    last_checked: datetime | None = None
    url_looks_like_careers: bool | None = None
    open_role_count: int
    roles: list[PublicJobResponse]
