"""Load official programme names, and remove those rows.

``init_db`` calls ``upgrade`` only. ``downgrade`` deletes rows whose
``external_id`` starts with ``verified:`` and sources of type
``verified_page``. Other vacancies stay. It is not called on boot.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.services.verified_programmes import import_verified_programmes


def upgrade(bind: Engine) -> None:
    """Store the verified programme rows once the vacancy table exists."""
    if "vacancies" not in inspect(bind).get_table_names():
        return
    columns = {col["name"] for col in inspect(bind).get_columns("vacancies")}
    if "opportunity_type" not in columns:
        return
    if bind.dialect.name == "postgresql" and "field_of_study" in columns:
        with bind.begin() as conn:
            conn.execute(text(
                "ALTER TABLE vacancies ALTER COLUMN field_of_study TYPE VARCHAR(400)"
            ))
    import_verified_programmes(bind)


def downgrade(bind: Engine) -> None:
    """Remove only the rows and sources this upgrade added."""
    tables = set(inspect(bind).get_table_names())
    if "vacancies" not in tables:
        return
    with bind.begin() as conn:
        if "vacancy_requirements" in tables:
            conn.execute(text(
                "DELETE FROM vacancy_requirements WHERE vacancy_id IN "
                "(SELECT id FROM vacancies WHERE external_id LIKE 'verified:%')"
            ))
        conn.execute(text("DELETE FROM vacancies WHERE external_id LIKE 'verified:%'"))
        if "vacancy_sources" in tables:
            conn.execute(text(
                "DELETE FROM vacancy_sources WHERE ats_type = 'verified_page' "
                "AND id NOT IN (SELECT source_id FROM vacancies)"
            ))
