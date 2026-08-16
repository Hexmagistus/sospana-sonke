"""Seed the company database from the bundled CSV, then optionally create an admin.

Usage:
    python -m scripts.import_companies                # import seed CSV
    python -m scripts.import_companies --admin EMAIL PASSWORD   # also create an admin

Run from the backend/ directory with the virtual environment active.
"""
import sys
from pathlib import Path

from app.core import security
from app.db.session import SessionLocal, init_db
from app.models.user import User
from app.services.csv_import import import_companies_from_csv

SEED = Path(__file__).resolve().parent.parent / "seed" / "company_database_import.csv"


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = import_companies_from_csv(db, SEED.read_bytes())
        print(f"Imported companies: created={result.created} updated={result.updated} "
              f"skipped={result.skipped} total_rows={result.total_rows}")
        for err in result.errors:
            print("  !", err)

        if len(sys.argv) >= 4 and sys.argv[1] == "--admin":
            email, password = sys.argv[2].lower(), sys.argv[3]
            if db.query(User).filter(User.email == email).first():
                print(f"Admin {email} already exists.")
            else:
                db.add(User(email=email, password_hash=security.hash_password(password),
                            first_name="Admin", last_name="User", role="admin",
                            email_verified=True))
                db.commit()
                print(f"Created admin user {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
