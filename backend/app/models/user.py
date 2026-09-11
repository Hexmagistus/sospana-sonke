"""User account model (blueprint sections 9 & 15)."""
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Captured at registration (free text, candidate's own words) so admins have
    # it from day one, even before/without a full candidate profile.
    preferred_position: Mapped[str | None] = mapped_column(String(150), nullable=True)
    qualification_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 'candidate' or 'admin' (role-based access control, blueprint section 15)
    role: Mapped[str] = mapped_column(String(20), default="candidate", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
