"""Schemas for the Career Explorer (qualification -> adjacent career families)."""
from pydantic import BaseModel


class CareerOption(BaseModel):
    title: str
    open_vacancies: int  # live count from the vacancy index; honest, can be 0


class CareerFamilyResponse(BaseModel):
    label: str
    matched_on: str
    related_careers: list[CareerOption]
    note: str


class CareerExplorerResponse(BaseModel):
    based_on: str | None  # the qualification/occupation text actually used, for transparency
    families: list[CareerFamilyResponse]
