"""Add and remove the opportunity-type filter on saved alerts.

``init_db`` calls ``upgrade`` only. ``downgrade`` drops the column. An empty
value means any type. Existing alerts stay that way.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade(bind: Engine) -> None:
    if "role_alerts" not in inspect(bind).get_table_names():
        return
    present = {col["name"] for col in inspect(bind).get_columns("role_alerts")}
    if "opportunity_type" in present:
        return
    with bind.begin() as conn:
        conn.execute(text("ALTER TABLE role_alerts ADD COLUMN opportunity_type VARCHAR(32)"))


def downgrade(bind: Engine) -> None:
    if "role_alerts" not in inspect(bind).get_table_names():
        return
    present = {col["name"] for col in inspect(bind).get_columns("role_alerts")}
    if "opportunity_type" not in present:
        return
    with bind.begin() as conn:
        conn.execute(text("ALTER TABLE role_alerts DROP COLUMN opportunity_type"))
