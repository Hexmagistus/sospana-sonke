"""Create and drop the anonymous daily usage totals.

``init_db`` calls ``upgrade`` only. ``downgrade`` drops both tables and is
covered by a test on a private SQLite engine. It is not called on boot.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade(bind: Engine) -> None:
    """Create the daily search and click tables when they are missing."""
    with bind.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS usage_search_daily ("
            "id VARCHAR(36) PRIMARY KEY, "
            "day DATE NOT NULL, "
            "country VARCHAR(60) NOT NULL DEFAULT '', "
            "category VARCHAR(16) NOT NULL DEFAULT '', "
            "intent VARCHAR(20) NOT NULL, "
            "outcome VARCHAR(20) NOT NULL, "
            "result_bucket VARCHAR(12) NOT NULL, "
            "searches INTEGER NOT NULL DEFAULT 0, "
            "results_returned INTEGER NOT NULL DEFAULT 0, "
            "results_with_source INTEGER NOT NULL DEFAULT 0)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_usage_search_daily "
            "ON usage_search_daily (day, country, category, intent, outcome, result_bucket)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS usage_click_daily ("
            "id VARCHAR(36) PRIMARY KEY, "
            "day DATE NOT NULL, "
            "target_kind VARCHAR(12) NOT NULL, "
            "target_id VARCHAR(36) NOT NULL, "
            "clicks INTEGER NOT NULL DEFAULT 0)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_usage_click_daily "
            "ON usage_click_daily (day, target_kind, target_id)"
        ))


def downgrade(bind: Engine) -> None:
    """Drop the daily totals. The counts go with the tables."""
    with bind.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS usage_click_daily"))
        conn.execute(text("DROP TABLE IF EXISTS usage_search_daily"))
    assert "usage_search_daily" not in inspect(bind).get_table_names()
    assert "usage_click_daily" not in inspect(bind).get_table_names()
