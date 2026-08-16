"""AI provider abstraction (blueprint section 24).

All AI use goes through this interface so the provider/model can be swapped
centrally. Providers must NEVER invent facts — extraction returns only what is
supported by the source text, and everything is stored as an unconfirmed
suggestion for the candidate to verify.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict


class StructuredCV(TypedDict, total=False):
    full_name: str | None
    email: str | None
    phone: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    skills: list[dict]          # {name, category}
    languages: list[str]
    education: list[dict]       # {institution, qualification, field_of_study, level}
    work_experience: list[dict] # {employer, position, responsibilities, technologies}
    certifications: list[dict]  # {name, issuing_organization}


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def structure_cv(self, text: str) -> StructuredCV:
        """Extract a structured profile suggestion from CV text."""
        raise NotImplementedError
