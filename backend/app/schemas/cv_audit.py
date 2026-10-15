"""Schemas for the ATS CV Audit ("CV Doctor") feature."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_S = 300     # short field
_L = 2500    # long field (summary / bullet)


class RunAuditRequest(BaseModel):
    cv_id: str = Field(min_length=1, max_length=36)


class ApplyToProfileOptions(BaseModel):
    contact: bool = True
    skills: bool = True
    experience: bool = True
    education: bool = True
    certifications: bool = True


class ApplyToProfileResult(BaseModel):
    skills: int
    work_experience: int
    work_experience_updated: int
    education: int
    certifications: int
    profile_fields: list[str]
    skipped_duplicates: int


class ExperienceIn(BaseModel):
    position: str | None = Field(default=None, max_length=_S)
    employer: str | None = Field(default=None, max_length=_S)
    location: str | None = Field(default=None, max_length=_S)
    start: str | None = Field(default=None, max_length=40)
    end: str | None = Field(default=None, max_length=40)
    is_current: bool = False
    bullets: list[str] = Field(default_factory=list, max_length=25)
    needs_review: bool = False


class EducationIn(BaseModel):
    qualification: str | None = Field(default=None, max_length=_S)
    institution: str | None = Field(default=None, max_length=_S)
    date_text: str | None = Field(default=None, max_length=60)
    year: int | None = Field(default=None, ge=1940, le=2100)
    status: str = Field(default="completed", pattern="^(completed|in_progress|awaiting_conferral|unverified)$")
    nqf: str | None = Field(default=None, max_length=5)


class CertIn(BaseModel):
    name: str = Field(min_length=1, max_length=_S)
    issuer: str | None = Field(default=None, max_length=_S)
    year: str | None = Field(default=None, max_length=20)
    kind: str = Field(default="certification", max_length=20)
    status: str = Field(default="completed", max_length=20)


class RebuiltCV(BaseModel):
    """What the candidate may edit before downloading. Every string is capped
    so a hostile client can't push a multi-MB document through the renderer."""
    full_name: str | None = Field(default=None, max_length=120)
    headline: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    linkedin_url: str | None = Field(default=None, max_length=300)
    links: list[str] = Field(default_factory=list, max_length=3)
    summary: str | None = Field(default=None, max_length=_L)
    competencies: dict[str, list[str]] = Field(default_factory=dict)
    software: list[str] = Field(default_factory=list, max_length=30)
    experience: list[ExperienceIn] = Field(default_factory=list, max_length=20)
    education: list[EducationIn] = Field(default_factory=list, max_length=15)
    current_studies: list[EducationIn] = Field(default_factory=list, max_length=10)
    certifications: list[CertIn] = Field(default_factory=list, max_length=25)
    short_courses: list[CertIn] = Field(default_factory=list, max_length=25)
    in_progress_certs: list[CertIn] = Field(default_factory=list, max_length=10)
    registrations: list[CertIn] = Field(default_factory=list, max_length=10)
    projects: list[str] = Field(default_factory=list, max_length=10)
    achievements: list[str] = Field(default_factory=list, max_length=10)
    languages: list[str] = Field(default_factory=list, max_length=12)
    drivers_licence: str | None = Field(default=None, max_length=60)


class CVAuditSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    cv_id: str
    source_filename: str
    original_scores: dict
    final_scores: dict
    edited_by_candidate: bool
    created_at: datetime
    updated_at: datetime | None = None


class CVAuditResponse(CVAuditSummary):
    document_facts: dict
    findings: list
    weaknesses: list
    rebuilt: dict
    change_log: list
    stress: dict
    pages: int
    compact: bool
    limitations: list
    checklist: list
    directions: list
