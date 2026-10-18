"""Hashes that stop a deleted opportunity from being stored again.

Nothing in this module reads or writes a title, a description, or a salary.
"""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.models.opportunity_tombstone import OpportunityTombstone


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def public_id_hash(vacancy_id: str) -> str:
    return _sha(f"id\n{vacancy_id}")


def url_hash(company_id: str, url: str) -> str:
    """Hash of one employer's listing address, already stripped."""
    return _sha(f"url\n{company_id}\n{url}")


def identity_hashes(
    *,
    company_id: str,
    external_id: str | None,
    source_url: str | None,
    canonical_url: str | None,
    application_url: str | None,
    fingerprint: str | None,
    board_url: str | None,
) -> list[str]:
    """Hashes of this role's own id or address. A shared careers board URL is not one."""
    found: list[str] = []
    external = (external_id or "").strip().casefold()
    if external:
        found.append(_sha(f"external\n{company_id}\n{external}"))
    board = (board_url or "").strip()
    seen: set[str] = set()
    for url in (canonical_url, application_url, source_url):
        cleaned = (url or "").strip()
        if not cleaned or cleaned == board or cleaned in seen:
            continue
        seen.add(cleaned)
        found.append(url_hash(company_id, cleaned))
    if not external and fingerprint:
        found.append(_sha(f"fingerprint\n{fingerprint}"))
    return found


def public_id_was_deleted(db: Session, vacancy_id: str) -> bool:
    digest = public_id_hash(vacancy_id)
    return (
        db.query(OpportunityTombstone.key_hash)
        .filter(OpportunityTombstone.key_hash == digest)
        .first()
        is not None
    )


def listing_was_deleted(
    db: Session,
    *,
    company_id: str,
    external_id: str | None,
    source_url: str | None,
    canonical_url: str | None,
    application_url: str | None,
    fingerprint: str | None,
    board_url: str | None,
) -> bool:
    hashes = identity_hashes(
        company_id=company_id,
        external_id=external_id,
        source_url=source_url,
        canonical_url=canonical_url,
        application_url=application_url,
        fingerprint=fingerprint,
        board_url=board_url,
    )
    if not hashes:
        return False
    return (
        db.query(OpportunityTombstone.key_hash)
        .filter(OpportunityTombstone.key_hash.in_(hashes))
        .first()
        is not None
    )
