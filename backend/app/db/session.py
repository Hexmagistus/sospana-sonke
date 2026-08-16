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
