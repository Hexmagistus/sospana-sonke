"""Schema for interview preparation."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class InterviewPrepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    match_id: str | None
    vacancy_id: str | None
    content: dict
    generated_by: str
    created_at: datetime
