"""Record expired opportunities without deleting them.

``upgrade`` adds ``vacancies.status`` (``active`` or ``expired``) and
``vacancies.expired_at``, then stamps rows whose closing day has ended in
South Africa or that the scanner already marked closed or gone.

``downgrade`` drops those two columns. The vacancy rows stay.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def _columns(bind: Engine) -> set[str]:
    if "vacancies" not in inspect(bind).get_table_names():
        return set()
    return {col["name"] for col in inspect(bind).get_columns("vacancies")}


def upgrade(bind: Engine) -> None:
    """Add the columns when missing, then stamp rows that are already closed."""
    if "vacancies" not in inspect(bind).get_table_names():
        return
    present = _columns(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    ts = "TIMESTAMP" if is_sqlite else "TIMESTAMP WITH TIME ZONE"
    statements: list[str] = []
    if "status" not in present:
        statements.append(
            "ALTER TABLE vacancies ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'"
        )
    if "expired_at" not in present:
        statements.append(f"ALTER TABLE vacancies ADD COLUMN expired_at {ts}")
    if statements:
        with bind.begin() as conn:
            for sql in statements:
                conn.execute(text(sql))
    with bind.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_vacancies_status ON vacancies (status)"
        ))
    from app.services.opportunity_expiry import stamp_expired

    db = Session(bind)
    try:
        stamp_expired(db)
    finally:
        db.close()


def downgrade(bind: Engine) -> None:
    """Drop the expiry columns. Every vacancy row remains."""
    if "vacancies" not in inspect(bind).get_table_names():
        return
    present = _columns(bind)
    with bind.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_vacancies_status"))
        for column in ("expired_at", "status"):
            if column in present:
                conn.execute(text(f"ALTER TABLE vacancies DROP COLUMN {column}"))
