"""Create and drop ``role_alerts``.

``init_db`` calls ``upgrade`` only. ``downgrade`` drops the table and is
covered by a test on a private SQLite engine. It is not called on boot.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade(bind: Engine) -> None:
    """Create ``role_alerts`` and its user index when they are missing."""
    insp = inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    ts = "TIMESTAMP" if is_sqlite else "TIMESTAMP WITH TIME ZONE"
    flag = "BOOLEAN NOT NULL DEFAULT 1" if is_sqlite else "BOOLEAN NOT NULL DEFAULT TRUE"
    with bind.begin() as conn:
        if "role_alerts" not in insp.get_table_names():
            conn.execute(text(
                "CREATE TABLE role_alerts ("
                "id VARCHAR(36) PRIMARY KEY, "
                "user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "country VARCHAR(60), "
                "category VARCHAR(10), "
                "keyword VARCHAR(80), "
                f"active {flag}, "
                f"created_at {ts}, "
                f"updated_at {ts}, "
                f"deleted_at {ts})"
            ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_role_alerts_user_active ON role_alerts (user_id, active)"
        ))


def downgrade(bind: Engine) -> None:
    """Drop ``role_alerts``. Rows in the table go with it."""
    with bind.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS role_alerts"))
