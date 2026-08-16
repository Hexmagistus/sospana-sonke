"""SQLAlchemy declarative base and common column mixins."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Soft-delete marker (blueprint section 9): records are retained for audit,
    # not physically removed, unless a data-deletion request requires otherwise.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UUIDMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
