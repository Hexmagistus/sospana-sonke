"""One interface in front of the existing ATS strategies.

A new employer feed is a ``ScrapeStrategy`` registered in ``get_strategy``.
This wrapper gives that strategy discover / extract / normalize / validate
without a second copy of the scanner. ``validate`` reports gaps. It does not
invent values and it does not drop a listing that has a title.
"""
from __future__ import annotations

from typing import Protocol

import httpx

from app.scraper.base import RawVacancy, ScrapeStrategy, get_strategy
from app.scraper.normalise import prepare_listing


class ListingAdapter(Protocol):
    name: str

    def discover(self, source, client: httpx.Client) -> list[RawVacancy]:
        ...

    def extract(self, raw: RawVacancy) -> RawVacancy:
        ...

    def normalize(self, raw: RawVacancy, *, company_id: str, company_name: str | None,
                  company_country: str | None, source_url: str | None) -> dict:
        ...

    def validate(self, fields: dict) -> list[str]:
        ...


class StrategyAdapter:
    def __init__(self, strategy: ScrapeStrategy) -> None:
        self._strategy = strategy
        self.name = getattr(strategy, "ats_type", "unknown")

    def discover(self, source, client: httpx.Client) -> list[RawVacancy]:
        return self._strategy.fetch(source, client)

    def extract(self, raw: RawVacancy) -> RawVacancy:
        return raw

    def normalize(self, raw: RawVacancy, *, company_id: str, company_name: str | None,
                  company_country: str | None, source_url: str | None) -> dict:
        return prepare_listing(
            raw, company_id=company_id, company_name=company_name,
            company_country=company_country, source_url=source_url,
        )

    def validate(self, fields: dict) -> list[str]:
        missing: list[str] = []
        if not (fields.get("title") or "").strip():
            missing.append("title")
        return missing


def adapter_for(ats_type: str) -> StrategyAdapter:
    return StrategyAdapter(get_strategy(ats_type))
