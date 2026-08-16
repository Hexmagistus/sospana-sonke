"""Schemas for candidate matches and match configuration."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MatchResponse(BaseModel):
    id: str
    vacancy_id: str
    vacancy_title: str | None = None
    company_name: str | None = None
    score: float
    band: str
    decision: str
    confidence: str
    hard_ok: bool
    status: str
    created_at: datetime


class MatchDetailResponse(MatchResponse):
    sub_scores: dict
    reasons: list[str]
    gaps: list[str]
    engine_version: str


class MatchRunResponse(BaseModel):
    considered: int
    prefiltered_out: int
    matched: int
    rejected: int
    created: int
    updated: int


class MatchWeights(BaseModel):
    qualification: float = 25
    experience: float = 25
    skills: float = 20
    title: float = 10
    industry: float = 5
    location: float = 5
    certification: float = 5
    other: float = 5


class MatchConfigSchema(BaseModel):
    weights: MatchWeights = Field(default_factory=MatchWeights)
    apply_threshold: float = 80.0
    review_threshold: float = 60.0
    bands: dict = Field(default_factory=lambda: {"strong": 85, "good": 75, "possible": 65, "weak": 55})
