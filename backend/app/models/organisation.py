"""Organisation accounts, plan prices, and employer-submitted opportunities.

Job seekers stay on the candidate role. An organisation is a separate account
that can claim one directory row. Prices live in employer_plan_config and stay
unpublished until an administrator sets them. Card numbers are never stored.
"""
from datetime import datetime, date

from sqlalchemy import String, Integer, Text, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin

CLAIM_STATUSES = ("pending_email", "pending_admin", "verified", "rejected")
PLAN_CODES = ("free", "pro", "featured")
PAID_PLAN_CODES = ("pro", "featured")
OPPORTUNITY_STATUSES = ("pending", "approved", "rejected")
ENTITLEMENT_STATUSES = ("active", "cancelled", "refunded", "expired")
INVOICE_STATUSES = ("pending", "paid", "failed", "refunded", "refund_requested", "cancelled")


class EmployerAccount(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employer_accounts"
    __table_args__ = (UniqueConstraint("user_id", name="uq_employer_account_user"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_email")
    method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    work_email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    public_blurb: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_headline: Mapped[str | None] = mapped_column(String(160), nullable=True)


class EmployerPlanConfig(UUIDMixin, TimestampMixin, Base):
    """Admin-editable ZAR prices. A null amount means the owner has not set one."""

    __tablename__ = "employer_plan_config"
    __table_args__ = (UniqueConstraint("plan_code", name="uq_employer_plan_code"),)

    plan_code: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_zar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ZAR")
    post_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_note: Mapped[str] = mapped_column(String(80), nullable=False, default="TBD by owner")
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    includes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class EmployerOpportunity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employer_opportunities"

    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employer_accounts.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    company_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    opportunity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="job")
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    application_url: Mapped[str] = mapped_column(Text, nullable=False)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(400), nullable=True)
    stipend_text: Mapped[str | None] = mapped_column(String(240), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    provenance: Mapped[str] = mapped_column(String(40), nullable=False, default="employer-submitted")
    vacancy_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class EmployerEntitlement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employer_entitlements"

    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employer_accounts.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    plan_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vacancy_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    invoice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class EmployerInvoice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employer_invoices"
    __table_args__ = (UniqueConstraint("provider", "provider_reference", name="uq_employer_invoice_ref"),)

    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employer_accounts.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    plan_code: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_zar: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ZAR")
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    vacancy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmployerPaymentEvent(UUIDMixin, TimestampMixin, Base):
    """One processed provider event. The body stored is the reference and amount only."""

    __tablename__ = "employer_payment_events"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_reference", "event_name", name="uq_employer_payment_event",
        ),
    )

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    event_name: Mapped[str] = mapped_column(String(60), nullable=False)
    invoice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    amount_zar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(40), nullable=True)


class EmployerCorrection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employer_corrections"

    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employer_accounts.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    company_id: Mapped[str] = mapped_column(String(36), nullable=False)
    field_name: Mapped[str] = mapped_column(String(40), nullable=False)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class EmployerAuditEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employer_audit_events"

    actor_user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail: Mapped[str] = mapped_column(String(500), nullable=False, default="")
