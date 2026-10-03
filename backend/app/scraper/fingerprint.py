"""Stable vacancy identity.

Prefer the employer's own job id. Otherwise use the normalised title and
location. The description is deliberately not part of the key: a wording
tweak on the next scan must update the same row, not insert another one.
"""
from __future__ import annotations

import hashlib
import re


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def vacancy_fingerprint(company_id: str, external_id: str | None,
                        title: str | None, location: str | None) -> str:
    if _norm(external_id):
        basis = f"{company_id}|id|{_norm(external_id)}"
    else:
        basis = f"{company_id}|tl|{_norm(title)}|{_norm(location)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()
