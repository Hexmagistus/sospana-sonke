"""Copy one directory row from one SQLite database into another.

This does not open Neon and does not read DATABASE_URL. It is the restore
drill we can run without production credentials: build the schema, write a
row, copy it, and read it back.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.company import Company


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def run_restore_drill() -> dict:
    source = _engine()
    restored = _engine()
    Base.metadata.create_all(bind=source)
    Base.metadata.create_all(bind=restored)
    Source = sessionmaker(bind=source)
    Restored = sessionmaker(bind=restored)
    origin = Source()
    try:
        origin.add(Company(
            company_name="Restore Drill",
            country="South Africa",
            source_type="PRIVATE",
            active=True,
        ))
        origin.commit()
        saved = origin.query(Company).filter(Company.company_name == "Restore Drill").one()
        payload = {
            "company_name": saved.company_name,
            "country": saved.country,
            "source_type": saved.source_type,
            "active": saved.active,
        }
    finally:
        origin.close()

    copy = Restored()
    try:
        copy.add(Company(**payload))
        copy.commit()
        found = copy.query(Company).filter(Company.company_name == "Restore Drill").one()
        result = {
            "company_name": found.company_name,
            "country": found.country,
            "source_type": found.source_type,
            "active": bool(found.active),
        }
    finally:
        copy.close()
        source.dispose()
        restored.dispose()
    return result
