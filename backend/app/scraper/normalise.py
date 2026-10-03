"""Turn one raw listing into the columns we store.

Missing values stay None. Nothing here invents a city, a salary, or a
country the source did not give us. South African provinces still come from
the existing city list; other countries keep province empty.
"""
from __future__ import annotations

import re

from app.scraper.base import RawVacancy
from app.scraper.extract import (
    classify_requirements, infer_province, infer_work_mode, normalize_date,
    parse_salary_range, infer_nqf_level, content_hash, _CITY_TO_PROVINCE,
)
from app.scraper.fingerprint import vacancy_fingerprint
from app.scraper.quality import quality_score
from app.scraper.urls import canonical_listing_url, safe_application_url, source_domain


_CLOSED_PHRASES = (
    "this position has been filled",
    "this vacancy has been filled",
    "no longer accepting applications",
    "applications are now closed",
    "vacancy has closed",
    "position has been closed",
)

_EMPLOYMENT = (
    ("full time", "full_time"),
    ("fulltime", "full_time"),
    ("permanent", "full_time"),
    ("part time", "part_time"),
    ("parttime", "part_time"),
    ("contract", "contract"),
    ("freelance", "contract"),
    ("intern", "intern"),
    ("temporary", "temporary"),
    ("fixed term", "temporary"),
)


# Matches Vacancy.external_id. A Workday externalPath longer than this keeps
# its tail, because the requisition id is the last token, not the first.
_EXTERNAL_ID_MAX = 2000


def fit_external_id(value: str | None) -> str | None:
    """Store the employer's own vacancy id, including a long Workday path."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= _EXTERNAL_ID_MAX:
        return text
    return text[-_EXTERNAL_ID_MAX:]


def listing_explicitly_closed(title: str | None, description: str | None) -> bool:
    blob = f"{title or ''} {description or ''}".lower()
    return any(phrase in blob for phrase in _CLOSED_PHRASES)


def normalise_employment_type(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    text = re.sub(r"[\s_\-]+", " ", str(value).strip().lower())
    for needle, label in _EMPLOYMENT:
        if needle in text:
            return label
    return text[:60]


def detect_currency(salary_text: str | None) -> str | None:
    if not salary_text:
        return None
    if re.search(r"\bZAR\b", salary_text, re.I) or re.search(r"\bR\s*\d", salary_text):
        return "ZAR"
    if re.search(r"\bUSD\b", salary_text, re.I) or "$" in salary_text:
        return "USD"
    if re.search(r"\bEUR\b", salary_text, re.I) or "€" in salary_text:
        return "EUR"
    if re.search(r"\bGBP\b", salary_text, re.I) or "£" in salary_text:
        return "GBP"
    if re.search(r"\b(NAD|BWP|KES|NGN|GHS|MUR)\b", salary_text, re.I):
        return re.search(r"\b(NAD|BWP|KES|NGN|GHS|MUR)\b", salary_text, re.I).group(1).upper()
    return None


def infer_city(location: str | None) -> str | None:
    if not location:
        return None
    text = location.lower()
    for city in sorted(_CITY_TO_PROVINCE, key=len, reverse=True):
        if city in text:
            return " ".join(part.capitalize() for part in city.split())
    return None


def _joined(rows: list[dict], category: str | None = None) -> str | None:
    texts = []
    for row in rows:
        if category is not None and row.get("category") != category:
            continue
        text = (row.get("text") or "").strip()
        if text:
            texts.append(text)
    if not texts:
        return None
    return "\n".join(texts)[:4000]


def prepare_listing(raw: RawVacancy, *, company_id: str, company_name: str | None,
                    company_country: str | None, source_url: str | None) -> dict:
    description = (raw.description or "").strip() or None
    title = (raw.title or "").strip()
    application_url = safe_application_url(raw.application_url)
    listing_url = raw.source_url or application_url or source_url
    canonical = canonical_listing_url(application_url or listing_url)
    closing = normalize_date(raw.closing_date)
    salary_min, salary_max = parse_salary_range(raw.salary)
    requirements = classify_requirements(description)
    closed = listing_explicitly_closed(title, description)
    location = (raw.location or "").strip() or None
    external_id = fit_external_id(raw.external_id)
    return {
        "external_id": external_id,
        "title": title[:300],
        "department": (raw.department or "").strip()[:200] or None,
        "location": location[:200] if location else None,
        "city": infer_city(location),
        "country": (company_country or "").strip()[:60] or None,
        "work_mode": infer_work_mode(raw),
        "employment_type": normalise_employment_type(raw.employment_type),
        "salary": (raw.salary or "").strip()[:120] or None,
        "salary_currency": detect_currency(raw.salary),
        "posting_date": normalize_date(raw.posting_date),
        "closing_date": closing,
        "description": description,
        "requirements_text": _joined(requirements),
        "qualifications": _joined(requirements, "qualification"),
        "experience": _joined(requirements, "experience"),
        "application_url": application_url,
        "source_url": (raw.source_url or source_url or "")[:2000] or None,
        "canonical_url": canonical,
        "source_domain": source_domain(canonical or listing_url),
        "province": infer_province(location),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "nqf_level": infer_nqf_level(title, description),
        "content_hash": content_hash(company_id, raw),
        "fingerprint": vacancy_fingerprint(company_id, external_id, title, location),
        "lifecycle_status": "CLOSED" if closed else "ACTIVE",
        "verification_state": "DISCOVERED",
        "quality_score": quality_score(
            title=title, employer=company_name, location=location,
            description=description, application_url=application_url,
            closing_date=closing, external_id=external_id,
        ),
        "is_open": not closed,
        "requirement_rows": requirements,
        "raw_content": str(raw.raw)[:100000] if raw.raw else None,
    }
