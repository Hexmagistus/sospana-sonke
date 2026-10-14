"""Create and drop organisation plans, claims, invoices, and audit rows.

``init_db`` calls ``upgrade`` only. ``downgrade`` drops the tables and is
covered by a test. It is not called on boot.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_TABLES = (
    "employer_audit_events",
    "employer_corrections",
    "employer_payment_events",
    "employer_invoices",
    "employer_entitlements",
    "employer_opportunities",
    "employer_plan_config",
    "employer_accounts",
)


def upgrade(bind: Engine) -> None:
    """Create the organisation tables and seed unpublished plan rows."""
    with bind.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_accounts ("
            "id VARCHAR(36) PRIMARY KEY, "
            "user_id VARCHAR(36) NOT NULL, "
            "company_id VARCHAR(36) NOT NULL, "
            "status VARCHAR(20) NOT NULL, "
            "method VARCHAR(20), "
            "work_email VARCHAR(255) NOT NULL, "
            "token_hash VARCHAR(64), "
            "token_expires_at TIMESTAMP, "
            "verified_at TIMESTAMP, "
            "approved_by VARCHAR(36), "
            "review_note VARCHAR(500), "
            "public_blurb TEXT, "
            "contact_email VARCHAR(255), "
            "brand_headline VARCHAR(160), "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_employer_account_user ON employer_accounts (user_id)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_employer_accounts_company ON employer_accounts (company_id)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_plan_config ("
            "id VARCHAR(36) PRIMARY KEY, "
            "plan_code VARCHAR(20) NOT NULL, "
            "amount_zar INTEGER, "
            "currency VARCHAR(3) NOT NULL, "
            "post_limit INTEGER, "
            "duration_days INTEGER, "
            "label VARCHAR(80) NOT NULL, "
            "owner_note VARCHAR(80) NOT NULL, "
            "published BOOLEAN NOT NULL, "
            "includes TEXT NOT NULL, "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_employer_plan_code ON employer_plan_config (plan_code)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_opportunities ("
            "id VARCHAR(36) PRIMARY KEY, "
            "account_id VARCHAR(36) NOT NULL, "
            "company_id VARCHAR(36) NOT NULL, "
            "title VARCHAR(300) NOT NULL, "
            "opportunity_type VARCHAR(32) NOT NULL, "
            "location VARCHAR(200), "
            "country VARCHAR(80), "
            "description TEXT NOT NULL, "
            "application_url TEXT NOT NULL, "
            "closing_date DATE, "
            "field_of_study VARCHAR(400), "
            "stipend_text VARCHAR(240), "
            "status VARCHAR(20) NOT NULL, "
            "provenance VARCHAR(40) NOT NULL, "
            "vacancy_id VARCHAR(36), "
            "reviewed_by VARCHAR(36), "
            "reviewed_at TIMESTAMP, "
            "rejection_note VARCHAR(500), "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_employer_opportunities_account ON employer_opportunities (account_id)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_entitlements ("
            "id VARCHAR(36) PRIMARY KEY, "
            "account_id VARCHAR(36) NOT NULL, "
            "plan_code VARCHAR(20) NOT NULL, "
            "status VARCHAR(20) NOT NULL, "
            "starts_at TIMESTAMP NOT NULL, "
            "ends_at TIMESTAMP NOT NULL, "
            "cancel_at_period_end BOOLEAN NOT NULL, "
            "vacancy_id VARCHAR(36), "
            "opportunity_id VARCHAR(36), "
            "invoice_id VARCHAR(36), "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_invoices ("
            "id VARCHAR(36) PRIMARY KEY, "
            "account_id VARCHAR(36) NOT NULL, "
            "plan_code VARCHAR(20) NOT NULL, "
            "amount_zar INTEGER NOT NULL, "
            "currency VARCHAR(3) NOT NULL, "
            "provider VARCHAR(20) NOT NULL, "
            "provider_reference VARCHAR(120) NOT NULL, "
            "status VARCHAR(20) NOT NULL, "
            "vacancy_id VARCHAR(36), "
            "opportunity_id VARCHAR(36), "
            "paid_at TIMESTAMP, "
            "refunded_at TIMESTAMP, "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_employer_invoice_ref "
            "ON employer_invoices (provider, provider_reference)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_payment_events ("
            "id VARCHAR(36) PRIMARY KEY, "
            "provider VARCHAR(20) NOT NULL, "
            "provider_reference VARCHAR(120) NOT NULL, "
            "event_name VARCHAR(60) NOT NULL, "
            "invoice_id VARCHAR(36), "
            "amount_zar INTEGER, "
            "provider_status VARCHAR(40), "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_employer_payment_event "
            "ON employer_payment_events (provider, provider_reference, event_name)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_corrections ("
            "id VARCHAR(36) PRIMARY KEY, "
            "account_id VARCHAR(36) NOT NULL, "
            "company_id VARCHAR(36) NOT NULL, "
            "field_name VARCHAR(40) NOT NULL, "
            "proposed_value TEXT NOT NULL, "
            "status VARCHAR(20) NOT NULL, "
            "reviewed_by VARCHAR(36), "
            "review_note VARCHAR(500), "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS employer_audit_events ("
            "id VARCHAR(36) PRIMARY KEY, "
            "actor_user_id VARCHAR(36), "
            "action VARCHAR(40) NOT NULL, "
            "account_id VARCHAR(36), "
            "target_id VARCHAR(36), "
            "detail VARCHAR(500) NOT NULL, "
            "created_at TIMESTAMP, "
            "updated_at TIMESTAMP, "
            "deleted_at TIMESTAMP)"
        ))
        _seed_plan(conn, "plan-free", "free", 0, 3, None, "Free", "Included. No charge.", 1,
                   "Claim the employer page, submit corrections, and post a limited number of opportunities. "
                   "Every post is checked before it is listed.")
        _seed_plan(conn, "plan-pro", "pro", None, 15, 30, "Employer Pro", "TBD by owner", 0,
                   "A branded page, a higher post limit, and aggregated click totals for the page and roles. "
                   "Counts only. No visitor identity.")
        _seed_plan(conn, "plan-featured", "featured", None, None, 7, "Featured listing", "TBD by owner", 0,
                   "A time-boxed Sponsored label on one approved opportunity. It is shown only when it matches "
                   "the search, it is capped on each results page, and it does not change the order of other rows.")


def _seed_plan(conn, row_id, code, amount, post_limit, duration, label, note, published, includes) -> None:
    exists = conn.execute(
        text("SELECT 1 FROM employer_plan_config WHERE plan_code = :code"),
        {"code": code},
    ).first()
    if exists:
        return
    conn.execute(
        text(
            "INSERT INTO employer_plan_config "
            "(id, plan_code, amount_zar, currency, post_limit, duration_days, label, owner_note, published, includes) "
            "VALUES (:id, :code, :amount, 'ZAR', :post_limit, :duration, :label, :note, :published, :includes)"
        ),
        {
            "id": row_id,
            "code": code,
            "amount": amount,
            "post_limit": post_limit,
            "duration": duration,
            "label": label,
            "note": note,
            "published": bool(published),
            "includes": includes,
        },
    )


def downgrade(bind: Engine) -> None:
    """Drop the organisation tables. Invoices and entitlements go with them."""
    with bind.begin() as conn:
        for name in _TABLES:
            conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
    names = set(inspect(bind).get_table_names())
    for name in _TABLES:
        assert name not in names
