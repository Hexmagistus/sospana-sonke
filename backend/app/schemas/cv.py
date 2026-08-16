"""Schemas for CV upload, parsing, and applying parsed data to the profile."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CVResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_filename: str
    content_type: str
    extension: str
    size_bytes: int
    file_hash: str
    is_original: bool
    parse_status: str
    parse_error: str | None
    ai_model: str | None
    created_at: datetime


class CVStructuredResponse(BaseModel):
    """The AI's structured suggestion, returned for candidate review (unconfirmed)."""
    cv_id: str
    parse_status: str
    ai_model: str | None
    structured: dict | None


class ApplyToProfileRequest(BaseModel):
    # Which sections of the parsed suggestion to import as unconfirmed records.
    skills: bool = True
    education: bool = True
    work_experience: bool = True
    certifications: bool = True
    contact_and_links: bool = True


class ApplyToProfileResult(BaseModel):
    skills_added: int
    education_added: int
    work_experience_added: int
    certifications_added: int
    profile_fields_filled: list[str]
