"""Company / careers-source model (blueprint sections 9 & 20).

This is the administrator-controlled JSE + State-Owned-Entity database that seeds
the vacancy discovery engine. Careers URLs are validated by the URL tester
(app/services/url_tester.py) rather than trusted blindly.
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class Company(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    company_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    jse_code: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    source_type: Mapped[str] = mapped_column(String(10), default="JSE", nullable=False)  # JSE | SOE
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(60), default="South Africa", nullable=False)

    careers_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_website: Mapped[str | None] = mapped_column(Text, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # pending | ok | needs_real_url | needs_review | no_url | error
    scraping_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    # URL-tester results
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_http_status: Mapped[int | None] = mapped_column(nullable=True)
    last_final_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_looks_like_careers: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Application-automation policy (blueprint sections 14 & 29). Admin-controlled.
    # auto = may submit automatically where no human step is required;
    # assisted = prepare/pre-fill only; manual/disabled = never automate.
    automation_mode: Mapped[str] = mapped_column(String(12), default="assisted", nullable=False)
    requires_login: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_captcha: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
