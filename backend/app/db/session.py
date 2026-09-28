"""Database engine and session management."""
import logging
import re
import time
from collections.abc import Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine, event
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
# 60s: a notification SELECT left idle across a failed SMTP call (Render free
# cannot reach SMTP) pinned AccessExclusiveLock and the next boot's ALTER TABLE
# never finished. The server aborts that session instead of holding the lock.
_IDLE_IN_TRANSACTION = "60s"
_connect_args = {"check_same_thread": False} if _is_sqlite else {
    "options": "-c idle_in_transaction_session_timeout=60000",
}
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
            "→ sospana-sonke-api-fra → DATABASE_URL. The direct host opens a real "
            "Postgres connection per checkout and is a poor fit for the free tier."
        )

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

if not _is_sqlite:
    @event.listens_for(engine, "connect")
    def _arm_idle_in_transaction_timeout(dbapi_connection, _connection_record):
        """Repeat the startup GUC in case a pooler drops libpq options.

        A failure here must not refuse the connection: lock_timeout on the
        DDL path is what keeps boot from hanging.
        """
        try:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute(
                    f"SET idle_in_transaction_session_timeout = '{_IDLE_IN_TRANSACTION}'"
                )
            finally:
                cursor.close()
            dbapi_connection.commit()
        except Exception:
            logger.warning(
                "Could not set idle_in_transaction_session_timeout", exc_info=True
            )


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
    # Before bootstrap imports the seed CSV. The import dedup key includes
    # country, so an alias row must already wear the canonical spelling or a
    # re-import inserts a second employer.
    normalise_country_names()


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
    ("users", "notify_opportunity_alerts", "BOOLEAN DEFAULT FALSE"),
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


# Postgres ALTER TABLE takes AccessExclusiveLock and waits forever by default.
# Two idle-in-transaction sessions from the previous instance blocked
# `notify_opportunity_alerts` and the deploy died as update_failed. Bound the
# wait, retry a few times, then skip so this process can finish booting.
DDL_LOCK_TIMEOUT = "5s"
DDL_STATEMENT_TIMEOUT = "15s"
DDL_ATTEMPTS = 3


def _postgres_ddl_guards() -> list[str]:
    """SET LOCAL so the pooled connection does not keep a 5s lock_timeout."""
    return [
        f"SET LOCAL lock_timeout = '{DDL_LOCK_TIMEOUT}'",
        f"SET LOCAL statement_timeout = '{DDL_STATEMENT_TIMEOUT}'",
    ]


def _execute_bounded(
    sql: str, params: dict | None = None, *, attempts: int = DDL_ATTEMPTS,
) -> int | None:
    """Run one statement under the boot lock/statement timeouts.

    Returns the rowcount, or None when every attempt failed. Never raises —
    a lock timeout must not hang boot. SET LOCAL so a pooled connection does
    not keep the 5s lock_timeout after the transaction ends.
    """
    from sqlalchemy import text

    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with engine.begin() as conn:
                if not _is_sqlite:
                    for guard in _postgres_ddl_guards():
                        conn.execute(text(guard))
                result = conn.execute(text(sql), params or {})
            return int(result.rowcount or 0)
        except Exception as exc:
            last = exc
            logger.warning(
                "Boot SQL attempt %s/%s failed: %s", attempt, attempts, sql, exc_info=True
            )
            if attempt < attempts:
                time.sleep(min(0.4 * attempt, 1.0))
    logger.error(
        "Skipping boot SQL after %s attempts so boot can continue: %s (%s)",
        attempts, sql, last,
    )
    return None


def _execute_ddl(sql: str, *, attempts: int = DDL_ATTEMPTS) -> bool:
    """Run one DDL statement. Never raises — a lock timeout skips the statement."""
    return _execute_bounded(sql, attempts=attempts) is not None


def normalise_country_names() -> int:
    """Rename known country-spelling aliases to the homepage spelling.

    Idempotent: a second boot matches zero rows. Uses the same lock and
    statement timeouts as DDL so a busy table cannot hang startup. Returns
    the number of rows renamed, or 0 if the statement was skipped.
    """
    from app.services.country_names import COUNTRY_ALIASES

    if not COUNTRY_ALIASES:
        return 0
    params: dict[str, str] = {}
    whens: list[str] = []
    for i, (alias, canonical) in enumerate(COUNTRY_ALIASES.items()):
        params[f"a{i}"] = alias
        params[f"c{i}"] = canonical
        whens.append(f"WHEN :a{i} THEN :c{i}")
    in_list = ", ".join(f":a{i}" for i in range(len(COUNTRY_ALIASES)))
    sql = (
        "UPDATE companies SET country = CASE country "
        + " ".join(whens)
        + f" END WHERE country IN ({in_list})"
    )
    updated = _execute_bounded(sql, params)
    if updated:
        logger.info("Normalised %s company country name(s) to the homepage spelling", updated)
    return updated or 0


def _add_new_columns() -> None:
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table, column, ddl_type in _NEW_COLUMNS:
        if table not in existing_tables:
            continue  # create_all just made it fresh, with every current column
        existing_columns = {c["name"] for c in inspector.get_columns(table)}
        if column in existing_columns:
            continue
        added = _execute_ddl(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
        if not added:
            # The app can boot on the previous schema. The next boot retries.
            logger.error(
                "Column %s.%s (%s) is still missing — writes touching it may fail "
                "until a later boot can take the lock.",
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
    for name, table, columns in _INDEXES:
        if not _execute_ddl(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"):
            logger.error(
                "Index %s on %s was not created; queries still run, just slower.",
                name, table,
            )
