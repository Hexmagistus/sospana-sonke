"""Scraper package: strategy framework, ATS strategies, and politeness controls."""
from app.scraper.base import (  # noqa: F401
    RawVacancy, ScrapeStrategy, detect_ats, get_strategy, html_to_text,
)
