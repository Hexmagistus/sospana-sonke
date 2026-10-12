"""Anonymous daily totals for the public search and for outbound clicks.

A row is a count, not a visit. There is no user id, no IP address, no cookie,
and no copy of the question. Search rows keep the parsed country, category,
and intent, plus whether the answer was empty, not enough data, or had
results, and a band for the result count. Click rows keep the employer or
role id and the day.
"""
from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class UsageSearchDaily(UUIDMixin, Base):
    __tablename__ = "usage_search_daily"
    __table_args__ = (
        UniqueConstraint(
            "day", "country", "category", "intent", "outcome", "result_bucket",
            name="ux_usage_search_daily",
        ),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    country: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    intent: Mapped[str] = mapped_column(String(20), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    result_bucket: Mapped[str] = mapped_column(String(12), nullable=False)
    searches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    results_returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    results_with_source: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UsageClickDaily(UUIDMixin, Base):
    __tablename__ = "usage_click_daily"
    __table_args__ = (
        UniqueConstraint("day", "target_kind", "target_id", name="ux_usage_click_daily"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    target_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
