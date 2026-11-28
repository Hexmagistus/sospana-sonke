"""Create and drop ``game_tester_requests`` (Gauteng Hustle Run tester sign-ups).

``init_db`` calls ``upgrade`` only. ``downgrade`` drops the table and is
covered by a test on a private SQLite engine. It is not called on boot.

Postgres DDL (already applied to production Neon on 2026-11-23):

    CREATE TABLE IF NOT EXISTS game_tester_requests (
      id VARCHAR(36) PRIMARY KEY,
      email VARCHAR(254) NOT NULL,
      name VARCHAR(120),
      user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
      created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
      status VARCHAR(12) NOT NULL DEFAULT 'pending',
      added_at TIMESTAMP WITH TIME ZONE);
    CREATE UNIQUE INDEX IF NOT EXISTS ux_game_tester_requests_email_lower
      ON game_tester_requests (lower(email));
    CREATE INDEX IF NOT EXISTS ix_game_tester_requests_status_created
      ON game_tester_requests (status, created_at);
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def upgrade(bind: Engine) -> None:
    """Create the table and its indexes when they are missing (idempotent)."""
    is_sqlite = bind.dialect.name == "sqlite"
    ts = "TIMESTAMP" if is_sqlite else "TIMESTAMP WITH TIME ZONE"
    now = "CURRENT_TIMESTAMP" if is_sqlite else "now()"
    with bind.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS game_tester_requests ("
            "id VARCHAR(36) PRIMARY KEY, "
            "email VARCHAR(254) NOT NULL, "
            "name VARCHAR(120), "
            "user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL, "
            f"created_at {ts} NOT NULL DEFAULT {now}, "
            "status VARCHAR(12) NOT NULL DEFAULT 'pending', "
            f"added_at {ts})"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_game_tester_requests_email_lower "
            "ON game_tester_requests (lower(email))"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_game_tester_requests_status_created "
            "ON game_tester_requests (status, created_at)"
        ))


def downgrade(bind: Engine) -> None:
    """Drop ``game_tester_requests``. Rows in the table go with it."""
    with bind.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS game_tester_requests"))
