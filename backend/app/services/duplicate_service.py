"""Duplicate vacancy detection (blueprint section 16).

Scan-time dedup (content_hash + external_id, in app.services.scan_service)
already prevents the *same* source scan from creating repeats. This catches the
remaining case: the same role genuinely posted more than once for a company
(re-advertised, posted to more than one board that got scraped separately, a
scraper picking it up again after the page's markup changed enough to shift the
content hash). Grouping is deliberately simple and explainable -- same company,
a near-identical title, and the same location -- not a fuzzy ML match, so an
admin can see exactly why two listings were grouped before merging them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.vacancy import Vacancy


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _normalize_location(location: str | None) -> str:
    return (location or "").lower().strip()


@dataclass
class DuplicateGroup:
    keep: Vacancy       # the oldest listing -- kept as canonical by default
    duplicates: list[Vacancy]


def find_duplicate_groups(db: Session, company_id: str | None = None, limit: int = 500) -> list[DuplicateGroup]:
    q = db.query(Vacancy).filter(Vacancy.is_open.is_(True), Vacancy.deleted_at.is_(None))
    if company_id:
        q = q.filter(Vacancy.company_id == company_id)
    vacancies = q.order_by(Vacancy.first_seen_at.asc()).limit(limit).all()

    buckets: dict[tuple[str, str, str], list[Vacancy]] = {}
    for v in vacancies:
        key = (v.company_id, _normalize_title(v.title), _normalize_location(v.location))
        buckets.setdefault(key, []).append(v)

    groups: list[DuplicateGroup] = []
    for members in buckets.values():
        if len(members) < 2:
            continue
        # Oldest first_seen_at is the canonical listing -- the one candidates
        # have already seen the longest, and the one with the best-established
        # match history.
        ordered = sorted(members, key=lambda v: v.first_seen_at)
        groups.append(DuplicateGroup(keep=ordered[0], duplicates=ordered[1:]))
    return groups


def merge_duplicates(db: Session, keep_id: str, duplicate_ids: list[str]) -> int:
    """Soft-closes each duplicate (is_open=False, deleted_at set, duplicate_of_id
    points at the canonical listing) -- never a hard delete, so the record and
    its own match/application history stay intact for audit."""
    from datetime import datetime, timezone

    keep = db.get(Vacancy, keep_id)
    if keep is None:
        return 0
    now = datetime.now(timezone.utc)
    merged = 0
    for dup_id in duplicate_ids:
        if dup_id == keep_id:
            continue
        dup = db.get(Vacancy, dup_id)
        if dup is None or dup.company_id != keep.company_id:
            continue  # never merge across different employers, even if asked
        dup.is_open = False
        dup.deleted_at = now
        dup.duplicate_of_id = keep_id
        merged += 1
    db.commit()
    return merged
