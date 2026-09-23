"""User account model (blueprint sections 9 & 15)."""
from sqlalchemy import String, Boolean, DateTime, Integer
from datetime import datetime
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
    # Session revocation. Every token carries the value it was issued under
    # ("tv"); bumping this invalidates all outstanding access/refresh/reset
    # tokens at once (password reset, "sign out everywhere", account deletion).
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Per-account brute-force lockout.
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # POPIA consent record: which privacy-policy version the user accepted, and when.
    # NULL = never accepted (accounts created before the consent flow, or Google sign-ups).
    policy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Temporary messaging. Opt-in: nobody can be messaged until they switch this on.
    allow_messages: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Set by an admin after a confirmed abuse report; the user can no longer send messages.
    messaging_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
