"""Tombstones for opportunities that were deleted after they expired.

``upgrade`` creates ``opportunity_tombstones`` (hash and deleted_at only).
``downgrade`` drops that table. It does not restore a deleted opportunity.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade(bind: Engine) -> None:
    if "opportunity_tombstones" in inspect(bind).get_table_names():
        return
    timestamp = "TIMESTAMP" if bind.dialect.name == "sqlite" else "TIMESTAMP WITH TIME ZONE"
    with bind.begin() as conn:
        conn.execute(text(
            "CREATE TABLE opportunity_tombstones ("
            "key_hash VARCHAR(64) PRIMARY KEY, "
            f"deleted_at {timestamp} NOT NULL)"
        ))


def downgrade(bind: Engine) -> None:
    if "opportunity_tombstones" not in inspect(bind).get_table_names():
        return
    with bind.begin() as conn:
        conn.execute(text("DROP TABLE opportunity_tombstones"))
