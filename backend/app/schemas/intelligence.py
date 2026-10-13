"""Public answer from the deterministic intelligence search. No advert body and no employer notes."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.vacancy import PublicJobResponse


class IntelligenceUnderstood(BaseModel):
    keywords: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    employer: str | None = None
    source_label: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    max_age_days: int | None = None
    careers_link_only: bool = False
    opportunity_type: str | None = None
    looking_for: str


class IntelligenceEmployer(BaseModel):
    id: str
    company_name: str
    country: str
    source_type: str
    careers_url: str | None = None
    last_checked: datetime | None = None
    url_looks_like_careers: bool | None = None
    open_vacancies: int = 0
    open_vacancies_known: bool = False


class LabourPoint(BaseModel):
    period: str
    label: str
    rate: str


class LabourCitation(BaseModel):
    """Where a labour figure came from. Present only when the question asked for one."""
    publisher: str
    title: str
    url: str
    licence_url: str
    release_date: str
    table: str
    place: str
    series: str
    points: list[LabourPoint] = Field(default_factory=list)


class IntelligenceSearchResponse(BaseModel):
    question: str
    understood: IntelligenceUnderstood
    llm: str = "disabled"
    enough_data: bool
    summary: str
    reading: str
    limitations: list[str]
    follow_ups: list[str] = Field(default_factory=list)
    vacancies: list[PublicJobResponse]
    vacancy_count: int
    employers: list[IntelligenceEmployer]
    employer_count: int
    with_link_count: int
    counted_at: datetime
    citation: LabourCitation | None = None
