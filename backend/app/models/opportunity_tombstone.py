"""A deleted opportunity, with no listing content.

The only columns are a hash and the time of deletion. The hash is of the
public id, the employer's listing id, or the listing's own address. The
title, description, employer name, and salary are not stored here.
"""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OpportunityTombstone(Base):
    __tablename__ = "opportunity_tombstones"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
