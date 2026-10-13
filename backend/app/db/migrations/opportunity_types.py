"""Add opportunity type columns to stored vacancies, and remove them.

``init_db`` calls ``upgrade`` only. ``downgrade`` drops the columns and is
covered by a test on a private SQLite engine. It is not called on boot.
Existing rows default to ``job``. The upgrade then labels a row only when
its title or description names exactly one programme type.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.services.opportunity_type import classify_stored


def _columns(bind: Engine) -> set[str]:
    if "vacancies" not in inspect(bind).get_table_names():
        return set()
    return {col["name"] for col in inspect(bind).get_columns("vacancies")}


def upgrade(bind: Engine) -> None:
    """Add the columns when missing, then classify stored rows once."""
    if "vacancies" not in inspect(bind).get_table_names():
        return
    present = _columns(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    ts = "TIMESTAMP" if is_sqlite else "TIMESTAMP WITH TIME ZONE"
    reviewed = "BOOLEAN NOT NULL DEFAULT 0" if is_sqlite else "BOOLEAN NOT NULL DEFAULT FALSE"
    statements: list[str] = []
    if "opportunity_type" not in present:
        statements.append(
            "ALTER TABLE vacancies ADD COLUMN opportunity_type VARCHAR(32) NOT NULL DEFAULT 'job'"
        )
    if "field_of_study" not in present:
        statements.append("ALTER TABLE vacancies ADD COLUMN field_of_study VARCHAR(200)")
    if "stipend_text" not in present:
        statements.append("ALTER TABLE vacancies ADD COLUMN stipend_text VARCHAR(240)")
    if "verified_at" not in present:
        statements.append(f"ALTER TABLE vacancies ADD COLUMN verified_at {ts}")
    if "opportunity_reviewed" not in present:
        statements.append(f"ALTER TABLE vacancies ADD COLUMN opportunity_reviewed {reviewed}")
    if statements:
        with bind.begin() as conn:
            for sql in statements:
                conn.execute(text(sql))
    with bind.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_vacancies_open_type "
            "ON vacancies (is_open, opportunity_type)"
        ))
    classify_stored(bind)


def downgrade(bind: Engine) -> None:
    """Drop the opportunity columns. Stored types go with them. Rows remain."""
    if "vacancies" not in inspect(bind).get_table_names():
        return
    present = _columns(bind)
    with bind.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_vacancies_open_type"))
        for column in (
            "opportunity_reviewed", "verified_at", "stipend_text",
            "field_of_study", "opportunity_type",
        ):
            if column in present:
                conn.execute(text(f"ALTER TABLE vacancies DROP COLUMN {column}"))
