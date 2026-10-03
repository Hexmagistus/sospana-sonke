"""Daily Spark opens: one row per member per day they chose to reveal the spark.

This is the whole streak "database": the streak is derived from these dates, so
there is no counter to drift or reset. A row is written only when the member
presses "Reveal today's spark" (never on page load, never by a background job),
holds just a user id and a calendar date, and is deleted with the account. Rows
older than ``RETENTION_DAYS`` are pruned on write (storage limitation, POPIA).
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

RETENTION_DAYS = 400


class SparkOpen(Base):
    __tablename__ = "spark_opens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # The Africa/Johannesburg calendar date the spark belongs to.
    spark_date: Mapped[date] = mapped_column(Date, primary_key=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
