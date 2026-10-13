"""A number that asked for SMS alerts. Nothing is sent from this row."""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class SmsAlert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sms_alerts"

    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
