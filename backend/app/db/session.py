"""Database engine and session management."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _normalise_db_url(url: str) -> str:
    # Managed Postgres providers (Neon, Render, Heroku) hand out `postgres://…`.
    # SQLAlchemy + psycopg2 needs the explicit driver scheme.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


DATABASE_URL = _normalise_db_url(settings.DATABASE_URL)

# SQLite needs a special flag for use across threads (dev/test only).
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. MVP bootstrap; Alembic migrations replace this in Step 0.5."""
    from app.db.base import Base
    from app import models  # noqa: F401  (ensures models are registered)
    Base.metadata.create_all(bind=engine)
    _add_new_columns()


# Base.metadata.create_all() above only creates TABLES that don't exist yet — it
# never adds a column to a table that's already live in a deployed database. So
# a column added to a model after its table first shipped also needs an entry
# here, or it silently never appears anywhere the table pre-dates the change
# (e.g. production). Each entry is (table, column, column DDL type); additive
# and idempotent, so this is always safe to run on every boot.
_NEW_COLUMNS: list[tuple[str, str, str]] = [
    ("users", "preferred_position", "VARCHAR(150)"),
    ("users", "qualification_name", "VARCHAR(200)"),
    ("companies", "favicon_url", "TEXT"),
    ("companies", "favicon_checked_at", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
    ("companies", "content_hash", "VARCHAR(64)"),
    ("companies", "content_checked_at", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
    ("companies", "content_changed_at", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
]


def _add_new_columns() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table, column, ddl_type in _NEW_COLUMNS:
        if table not in existing_tables:
            continue  # create_all just made it fresh, with every current column
        existing_columns = {c["name"] for c in inspector.get_columns(table)}
        if column in existing_columns:
            continue
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        except Exception:
            pass  # never let optional column backfill block startup
