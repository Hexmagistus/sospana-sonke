"""Schemas for candidate profile and child records."""
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProfileUpdate(BaseModel):
    city: str | None = None
    country: str | None = None
    work_authorization: str | None = None
    preferred_contact_method: str | None = Field(default=None, pattern="^(email|sms|phone)$")
    current_occupation: str | None = None
    desired_occupations: list[str] | None = None
    industries: list[str] | None = None
    years_experience: int | None = Field(default=None, ge=0, le=80)
    preferred_locations: list[str] | None = None
    work_mode_preference: str | None = Field(default=None, pattern="^(remote|hybrid|onsite|any)$")
    minimum_salary: int | None = Field(default=None, ge=0)
    willing_to_relocate: bool | None = None
    languages: list[str] | None = None
    drivers_licence: str | None = None
    professional_memberships: list[str] | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ProfileResponse(ProfileUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str


# ---- child records ----
class _ChildResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    confirmed_by_candidate: bool
    source: str


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    qualification: str | None = None
    field_of_study: str | None = None
    level: str | None = None
    completion_date: date | None = None


class EducationResponse(_ChildResponseBase, EducationCreate):
    pass


class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    issuing_organization: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None


class CertificationResponse(_ChildResponseBase, CertificationCreate):
    pass


class WorkExperienceCreate(BaseModel):
    employer: str = Field(min_length=1, max_length=200)
    position: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    responsibilities: str | None = None
    achievements: str | None = None
    technologies: list[str] | None = None
    industry: str | None = None


class WorkExperienceResponse(_ChildResponseBase, WorkExperienceCreate):
    pass


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, pattern="^(technical|software|soft|management|operational|other)$")


class SkillResponse(_ChildResponseBase, SkillCreate):
    pass
