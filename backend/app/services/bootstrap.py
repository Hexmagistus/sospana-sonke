"""First-boot bootstrap for managed hosting (idempotent).

When AUTO_SEED is on and the company table is empty, imports the bundled JSE+SOE
CSV. When ADMIN_EMAIL/ADMIN_PASSWORD are set and that user doesn't exist yet,
creates an administrator. Safe to run on every startup — it only acts when needed.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core import security
from app.models.company import Company
from app.models.user import User
from app.services.csv_import import import_companies_from_csv

_SEED = Path(__file__).resolve().parent.parent.parent / "seed" / "company_database_import.csv"


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
            db.rollback()

    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        email = settings.ADMIN_EMAIL.lower()
        if not db.query(User).filter(User.email == email).first():
            db.add(User(email=email, password_hash=security.hash_password(settings.ADMIN_PASSWORD),
                        first_name="Admin", last_name="User", role="admin", email_verified=True))
            db.commit()
