"""Boot against the vacancy table production had before the quality columns.

``init_db`` must add ``quality_score``, ``quality_flags``, the link columns,
the expiry columns, the tombstone table and the private file store before any
startup code selects a vacancy by ``external_id``.
"""
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.main import app
from app.models.vacancy import Vacancy


_OLD_VACANCIES = """
CREATE TABLE vacancies (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    company_id VARCHAR(36) NOT NULL,
    source_id VARCHAR(36) NOT NULL,
    external_id VARCHAR(200),
    title VARCHAR(300) NOT NULL,
    department VARCHAR(200),
    location VARCHAR(200),
    work_mode VARCHAR(20),
    employment_type VARCHAR(60),
    salary VARCHAR(120),
    posting_date DATE,
    closing_date DATE,
    description TEXT,
    application_url TEXT,
    source_url TEXT,
    raw_content TEXT,
    content_hash VARCHAR(64) NOT NULL,
    is_open BOOLEAN NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL
)
"""


def test_boot_adds_schema_before_the_external_id_query(tmp_path, monkeypatch):
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{tmp_path / 'previous.db'}")
    with engine.begin() as conn:
        conn.execute(text(_OLD_VACANCIES))
        conn.execute(text(
            "INSERT INTO vacancies (id, company_id, source_id, external_id, title, "
            "content_hash, is_open, first_seen_at, last_seen_at) VALUES "
            "('v1', 'c1', 's1', 'role-from-before', 'Nurse', 'hash', 1, "
            "'2026-10-01 00:00:00', '2026-10-01 00:00:00')"
        ))
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(vacancies)"))}
    assert "quality_flags" not in cols
    assert "quality_score" not in cols

    previous_engine = db_session.engine
    previous_session = db_session.SessionLocal
    bound = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", bound)
    try:
        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(vacancies)"))}
                tables = {row[0] for row in conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ))}
            assert {"quality_score", "quality_flags", "link_http_status", "link_checked_at",
                    "status", "expired_at"} <= cols
            assert "opportunity_tombstones" in tables
            assert "stored_files" in tables
            db = bound()
            try:
                row = db.query(Vacancy).filter(Vacancy.external_id == "role-from-before").one()
            finally:
                db.close()
            assert row.title == "Nurse"
            assert row.quality_flags is None
            assert row.quality_score is None
    finally:
        db_session.engine = previous_engine
        db_session.SessionLocal = previous_session
        engine.dispose()
