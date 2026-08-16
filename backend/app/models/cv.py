"""Uploaded CV model (blueprint section 4).

The original uploaded CV is stored immutably and never overwritten. Extracted
text and the AI-structured result are kept alongside it. Tailored CV *versions*
(generated later, per vacancy) are a separate table added in the documents module.
"""
from sqlalchemy import String, Integer, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class CV(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cvs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # sha256
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)

    # This is the untouched upload; True always for originals (never overwritten).
    is_original: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), default="uploaded", nullable=False)
    # uploaded | extracted | parsed | failed
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The AI-structured profile suggestion (not yet applied/confirmed by candidate).
    structured: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
