"""User account model (blueprint sections 9 & 15)."""
from sqlalchemy import String, Boolean, DateTime, Integer
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


# Role types a client can ask to be considered for. "any" = open to every kind of
# post; "none" = an explicit choice not to be considered right now.
POST_TYPES: dict[str, str] = {
    "any": "Any kind of post",
    "permanent": "Permanent",
    "contract": "Contract or fixed term",
    "part_time": "Part time",
    "internship": "Internship or work experience",
    "learnership": "Learnership or apprenticeship",
    "graduate": "Graduate programme",
    "none": "Don't consider me for posts right now",
}


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
    # Three client preferences. Each has its own "has chosen" state, separate
    # from the value: the *_chosen_at timestamp is NULL until the person picks
    # (NULL = not chosen yet), and yes / no / a role type is the value. A
    # default value with no timestamp means they have never been asked.
    #
    # 1. Tagging: an administrator may tag them to employers (put them forward).
    allow_tagging: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_tagging_chosen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 2. Preferred post: the kind of role they want to be considered for. One of
    #    POST_TYPES. NULL until chosen; "none" is an explicit "don't consider me".
    #    Not the free-text job title in preferred_position.
    preferred_post_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preferred_post_chosen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 3. Alerts: job alerts. The existing yes/no, plus the separate chosen state.
    notify_opportunity_alerts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_opportunity_alerts_chosen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # One service email asking them to choose. Claimed before the send so a retry cannot double-send.
    consent_prompt_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Admins only. Off by default: an optional email digest of client sign-ins.
    admin_login_digest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_login_digest_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Temporary messaging. Opt-in: nobody can be messaged until they switch this on.
    allow_messages: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Set by an admin after a confirmed abuse report; the user can no longer send messages.
    messaging_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @staticmethod
    def _choice_state(value: bool, chosen_at: datetime | None) -> str:
        """not_chosen, yes, or no. A legacy True with no timestamp still counts as yes."""
        if chosen_at is None and not value:
            return "not_chosen"
        return "yes" if value else "no"

    @property
    def tagging_state(self) -> str:
        return self._choice_state(bool(self.allow_tagging), self.allow_tagging_chosen_at)

    @property
    def alerts_state(self) -> str:
        return self._choice_state(
            bool(self.notify_opportunity_alerts), self.notify_opportunity_alerts_chosen_at,
        )

    @property
    def preferred_post_state(self) -> str:
        """not_chosen until a role type is picked; then chosen."""
        if self.preferred_post_chosen_at is None or not self.preferred_post_type:
            return "not_chosen"
        return "chosen"

    @property
    def tagging_allowed(self) -> bool:
        """An explicit yes. A missing choice and a no both mean admins must not tag this person."""
        return self.tagging_state == "yes"

    @property
    def consent_pending(self) -> bool:
        return "not_chosen" in (self.tagging_state, self.preferred_post_state, self.alerts_state)

    @property
    def show_consent_banner(self) -> bool:
        """Shown on sign-in while any of the three preferences is still not chosen.

        There is no dismiss: it goes away only when all three are chosen.
        """
        return bool(
            self.role == "candidate"
            and self.is_active
            and self.deleted_at is None
            and self.consent_pending
        )
