"""First-boot bootstrap for managed hosting (idempotent).

When AUTO_SEED is on and the company table is empty, imports the bundled JSE+SOE
CSV. When ADMIN_EMAIL/ADMIN_PASSWORD are set and that user doesn't exist yet,
creates an administrator. Safe to run on every startup — it only acts when needed.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core import security
from app.models.company import Company
from app.models.user import User
from app.services.csv_import import import_companies_from_csv

_SEED = Path(__file__).resolve().parent.parent.parent / "seed" / "company_database_import.csv"

# Sports clubs (as opposed to national sports associations) were seeded briefly and then
# withdrawn. The seed importer only adds/updates rows, so retire the leftovers here.
# Idempotent: only touches these exact names in the SPORT category.
_RETIRED_SPORT_CLUBS = [
    "Mamelodi Sundowns FC",
    "Kaizer Chiefs FC",
    "Orlando Pirates FC",
    "SuperSport United FC",
    "Cape Town City FC",
    "Stellenbosch FC",
    "AmaZulu FC",
    "TS Galaxy FC",
    "Golden Arrows FC",
    "Chippa United FC",
    "Richards Bay FC",
    "Polokwane City FC",
    "Vodacom Bulls",
    "DHL Stormers",
    "Hollywoodbets Sharks",
    "Emirates Lions",
    "Toyota Cheetahs",
    "Griquas Rugby",
    "SA20 League",
    "Titans Cricket",
    "Dolphins Cricket",
    "Warriors Cricket",
    "Lions Cricket",
    "Cape Cobras Cricket",
    "Knights Cricket",
    "Comrades Marathon Association",
    "Sunshine Tour (golf)",
    "Basketball National League (BNL)",
    "Cycling South Africa"
]


def _retire_withdrawn_rows(db: Session) -> None:
    from datetime import datetime, timezone
    try:
        rows = (
            db.query(Company)
            .filter(Company.source_type == "SPORT", Company.company_name.in_(_RETIRED_SPORT_CLUBS), Company.deleted_at.is_(None))
            .all()
        )
        for c in rows:
            c.deleted_at = datetime.now(timezone.utc)
            c.active = False
        if rows:
            db.commit()
            logger.info("Retired %d withdrawn sports club rows", len(rows))
    except Exception:
        logger.exception("Retiring withdrawn rows failed; rolled back")
        db.rollback()


def bootstrap(db: Session) -> None:
    if settings.AUTO_SEED and _SEED.exists():
        # Upsert the bundled company list on every boot so that deploying an
        # updated CSV keeps the live database in sync. The importer deduplicates
        # on (normalised name + JSE code), so this creates new companies and
        # refreshes existing ones without making duplicates. (Set AUTO_SEED=false
        # once you manage companies only through the admin UI.)
        try:
            import_companies_from_csv(db, _SEED.read_bytes())
        except Exception:
            logger.exception("Bootstrap CSV import failed; rolled back")
            db.rollback()

    _retire_withdrawn_rows(db)

    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        email = settings.ADMIN_EMAIL.lower()
        if not db.query(User).filter(User.email == email).first():
            db.add(User(email=email, password_hash=security.hash_password(settings.ADMIN_PASSWORD),
                        first_name="Admin", last_name="User", role="admin", email_verified=True))
            db.commit()
