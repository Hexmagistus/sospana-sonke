"""Company CSV importer (blueprint section 20).

Accepts the seed CSV (company_name, jse_code, careers_url, source_type, ...) and
upserts Company records. Deduplicates on a normalised company name + JSE code so
re-importing an updated file does not create duplicates.
"""
from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyImportResult

_EXPECTED = {"company_name"}


# careers_status values in the seed CSV that mean "a person confirmed this URL
# lands on the employer's own live careers/vacancies page". Rows carrying one of
# these are imported as scraping_status="ok" (the value the client-facing
# "live links" section keys on) so they show as live from day one. The scheduled
# URL tester still re-checks them and downgrades any link that later breaks.
_LIVE_CAREERS_STATUSES = {
    "green_verified", "green_confirmed", "direct vacancy list", "direct vacancies page",
    "direct careers page", "direct vacancies listing", "direct jobs page", "direct careers portal",
    "dedicated career opportunities page",
}
# Statuses only the URL tester writes; a re-import must not wipe them back to "pending".
_TESTER_STATUSES = {"ok", "needs_review", "needs_real_url", "error"}


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


def import_companies_from_csv(db: Session, content: bytes) -> CompanyImportResult:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not _EXPECTED.issubset({f.strip() for f in reader.fieldnames}):
        return CompanyImportResult(created=0, updated=0, skipped=0, total_rows=0,
                                   errors=["CSV must contain at least a 'company_name' column."])

    created = updated = skipped = total = 0
    errors: list[str] = []

    # Build an index of existing companies for dedup.
    existing: dict[tuple[str, str], Company] = {}
    for c in db.query(Company).all():
        existing[(_norm(c.company_name), (c.jse_code or "").strip().upper())] = c

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        total += 1
        name = (row.get("company_name") or "").strip()
        if not name:
            skipped += 1
            errors.append(f"Row {i}: missing company_name; skipped.")
            continue
        code = (row.get("jse_code") or "").strip().upper()
        key = (_norm(name), code)

        careers_url = (row.get("careers_url") or "").strip() or None
        source_type = (row.get("source_type") or "JSE").strip().upper()[:10] or "JSE"
        scraping_status = (row.get("scraping_status") or ("pending" if careers_url else "no_url")).strip()
        careers_status = (row.get("careers_status") or "").strip().lower()
        if careers_url and scraping_status in ("", "pending") and careers_status in _LIVE_CAREERS_STATUSES:
            scraping_status = "ok"
        active_raw = (row.get("active") or ("true" if careers_url else "false")).strip().lower()
        active = active_raw in ("true", "1", "yes", "y")
        notes = (row.get("relevance_note") or row.get("notes") or "").strip() or None
        country = (row.get("country") or "South Africa").strip() or "South Africa"
        official_website = (row.get("official_website") or "").strip() or None

        company = existing.get(key)
        if company is None:
            company = Company(company_name=name, jse_code=code or None)
            db.add(company)
            existing[key] = company
            created += 1
        else:
            updated += 1

        # Keep a URL tester verdict on re-import when the link itself is unchanged and the
        # CSV has nothing more definite to say (otherwise every boot would reset it to "pending").
        keep_tested = (
            company.id is not None and company.careers_url == careers_url
            and company.scraping_status in _TESTER_STATUSES and scraping_status == "pending"
        )
        company.source_type = source_type
        company.careers_url = careers_url
        if not keep_tested:
            company.scraping_status = scraping_status
        company.active = active
        company.notes = notes
        company.country = country
        if official_website:
            company.official_website = official_website

    db.commit()
    return CompanyImportResult(created=created, updated=updated, skipped=skipped,
                               total_rows=total, errors=errors[:50])
