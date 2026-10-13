"""Admin scorecard for the anonymous daily totals. No question text and no person."""
from pydantic import BaseModel, Field


class UsageDayCount(BaseModel):
    day: str
    searches: int
    searches_with_results: int
    searches_empty: int
    searches_not_enough_data: int
    clicks: int


class UsageClickTarget(BaseModel):
    target_kind: str
    target_id: str
    label: str
    clicks: int


class UsageScorecardResponse(BaseModel):
    window_days: int
    retention_days: int
    counted_on: str
    searches: int
    searches_with_results: int
    searches_empty: int
    searches_not_enough_data: int
    search_success_rate: float | None
    not_enough_data_rate: float | None
    clicks: int
    click_through_rate: float | None
    results_returned: int
    results_with_source: int
    source_link_rate: float | None
    definitions: dict[str, str]
    by_day: list[UsageDayCount] = Field(default_factory=list)
    clicks_by_target: list[UsageClickTarget] = Field(default_factory=list)
