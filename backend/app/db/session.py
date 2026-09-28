"""Database engine and session management."""
import logging
import re
from collections.abc import Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# Neon hostnames look like ep-name-pooler.us-west-2.aws.neon.tech. The region
# token is the AWS region, not a secret. The endpoint id before it is omitted.
_REGION_RE = re.compile(r"\b((?:us|eu|ap|sa|ca|af|me)-[a-z]+-\d+)\b")


def _normalise_db_url(url: str) -> str:
    # Managed Postgres providers (Neon, Render, Heroku) hand out `postgres://…`.
    # SQLAlchemy + psycopg2 needs the explicit driver scheme.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


DATABASE_URL = _normalise_db_url(settings.DATABASE_URL)


def describe_database(url: str | None = None) -> dict:
    """Non-secret facts about DATABASE_URL: pooled host, and the region in the hostname.

    Never returns the user, password, endpoint id, or database name. /health uses
    this so a deploy can be checked without opening the Render env screen.
    """
    raw = settings.DATABASE_URL if url is None else url
    if raw.startswith("sqlite"):
        return {"pooled": False, "region": None}
    host = urlparse(raw).hostname or ""
    if not host and "://" not in raw:
        host = ""
    match = _REGION_RE.search(host)
    return {"pooled": "-pooler" in host, "region": match.group(1) if match else None}


# SQLite needs a special flag for use across threads (dev/test only).
# Postgres gets a small pool that fits Render free (512 MB, one worker) and
# Neon's pooler. pool_recycle stays under 300s so idle connections are dropped
# before Neon closes them. pool_pre_ping stays: a dead connection would otherwise
# 500 the next request, and the ping is one round trip only on checkout.
_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs: dict = {"pool_pre_ping": True}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=5,
        max_overflow=2,
        pool_timeout=10,
        pool_recycle=240,
    )
    _info = describe_database()
    if not _info["pooled"]:
        logger.warning(
            "DATABASE_URL is not a Neon pooled connection (the host should contain "
            "'-pooler'). Paste the pooled string from the Neon dashboard into Render "
            "→ sospana-sonke-api → DATABASE_URL. The direct host opens a real "
            "Postgres connection per checkout and is a poor fit for the free tier."
        )

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
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
    _ensure_indexes()


# Base.metadata.create_all() above only creates TABLES that don't exist yet — it
# never adds a column to a table that's already live in a deployed database. So
# a column added to a model after its table first shipped also needs an entry
# here, or it silently never appears anywhere the table pre-dates the change
# (e.g. production). Each entry is (table, column, column DDL type); additive
# and idempotent, so this is always safe to run on every boot.
_NEW_COLUMNS: list[tuple[str, str, str]] = [
    ("users", "preferred_position", "VARCHAR(150)"),
    ("users", "qualification_name", "VARCHAR(200)"),
    ("users", "policy_accepted_at", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
    ("users", "policy_version", "VARCHAR(20)"),
    ("users", "allow_messages", "BOOLEAN DEFAULT FALSE"),
    ("users", "messaging_banned", "BOOLEAN DEFAULT FALSE"),
    ("users", "token_version", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "failed_login_count", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "locked_until", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
    ("companies", "favicon_url", "TEXT"),
    ("companies", "favicon_checked_at", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
    ("companies", "content_hash", "VARCHAR(64)"),
    ("companies", "content_checked_at", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
    ("companies", "content_changed_at", "TIMESTAMP WITH TIME ZONE" if not DATABASE_URL.startswith("sqlite") else "TIMESTAMP"),
    ("notifications", "link_url", "TEXT"),
    ("vacancies", "province", "VARCHAR(40)"),
    ("vacancies", "salary_min", "INTEGER"),
    ("vacancies", "salary_max", "INTEGER"),
    ("vacancies", "nqf_level", "INTEGER"),
    ("vacancies", "trust_flags", "JSON" if not DATABASE_URL.startswith("sqlite") else "TEXT"),
    ("vacancies", "duplicate_of_id", "VARCHAR(36)"),
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
            # Never let optional column backfill block startup -- but this used to
            # fail completely silently, which is a real data-integrity risk: the
            # app would carry on writing/reading a table that's missing a column
            # it expects, with no record anywhere of why. Log it loudly instead.
            logger.exception(
                "Failed to add column %s.%s (%s) -- schema may now be out of "
                "sync with the models; writes touching this column may fail.",
                table, column, ddl_type,
            )


# create_all() does not add indexes to tables that already exist in production.
# These are additive CREATE INDEX IF NOT EXISTS statements (sqlite and postgres
# both support that), so a boot never rewrites or locks out existing rows.
# They cover the directory filters (country + category, soft-delete) and the
# vacancy list's open/closing-date sweep.
_INDEXES: list[tuple[str, str, str]] = [
    ("ix_companies_country_type", "companies", "country, source_type"),
    ("ix_companies_deleted_at", "companies", "deleted_at"),
    # Directory list: WHERE deleted_at IS NULL ORDER BY company_name.
    ("ix_companies_deleted_name", "companies", "deleted_at, company_name"),
    ("ix_vacancies_open_closing", "vacancies", "is_open, closing_date"),
    # Vacancy list and the dashboard "listings last confirmed" stamp:
    # WHERE is_open ORDER BY / MAX(last_seen_at).
    ("ix_vacancies_open_last_seen", "vacancies", "is_open, last_seen_at"),
    # Public tip summary: WHERE hidden = false AND created_at > cutoff.
    ("ix_comments_visible_created", "company_comments", "hidden, created_at"),
    # Match list: WHERE user_id = ? ORDER BY score DESC.
    ("ix_matches_user_score", "candidate_matches", "user_id, score"),
]


def _ensure_indexes() -> None:
    from sqlalchemy import text

    for name, table, columns in _INDEXES:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))
        except Exception:
            logger.exception("Failed to create index %s on %s; queries still run, just slower.", name, table)
