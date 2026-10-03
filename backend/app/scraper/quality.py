"""Completeness score. This is not a confidence or legitimacy rating.

Seven fields the candidate can actually use. Each one that is present counts
the same. A high score means the listing is filled in, not that it was
verified.
"""
from __future__ import annotations


def quality_score(*, title: str | None, employer: str | None, location: str | None,
                  description: str | None, application_url: str | None,
                  closing_date, external_id: str | None) -> int:
    present = (
        bool((title or "").strip()),
        bool((employer or "").strip()),
        bool((location or "").strip()),
        bool((description or "").strip()),
        bool((application_url or "").strip()),
        closing_date is not None,
        bool((external_id or "").strip()),
    )
    return round(100 * sum(present) / len(present))
