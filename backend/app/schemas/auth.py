"""Request/response schemas for authentication."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.models.user import POST_TYPES


def _check_post_type(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if value not in POST_TYPES:
        raise ValueError("preferred_post_type must be one of: " + ", ".join(POST_TYPES))
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    mobile_number: str | None = Field(default=None, max_length=30)
    # Free text, in the candidate's own words — not validated against any list,
    # since neither is a structured taxonomy yet at registration time.
    preferred_position: str | None = Field(default=None, max_length=150)
    qualification_name: str | None = Field(default=None, max_length=200)
    # True when the user ticked the POPIA consent box (Privacy Policy + Terms).
    accepted_policy: bool = False
    # None means this registration did not show the choice (leave it unrecorded).
    # True or false means the person saw the box and picked.
    allow_tagging: bool | None = None
    # One of the post types in app.models.user.POST_TYPES; None = not chosen.
    preferred_post_type: str | None = Field(default=None, max_length=30)
    notify_opportunity_alerts: bool | None = None

    @field_validator("preferred_post_type")
    @classmethod
    def _post_type(cls, value: str | None) -> str | None:
        return _check_post_type(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp_code: str | None = None   # required when the account has MFA enabled


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleLoginRequest(BaseModel):
    credential: str   # the Google ID token (JWT) returned by Google Identity Services
    otp_code: str | None = None   # required when the linked account already has MFA


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    mobile_number: str | None
    preferred_position: str | None = None
    qualification_name: str | None = None
    email_verified: bool
    mfa_enabled: bool
    role: str
    policy_accepted_at: datetime | None = None
    policy_version: str | None = None
    allow_messages: bool = False
    allow_tagging: bool = False
    preferred_post_type: str | None = None
    notify_opportunity_alerts: bool = False
    tagging_state: str = "not_chosen"
    preferred_post_state: str = "not_chosen"
    alerts_state: str = "not_chosen"
    show_consent_banner: bool = False


class AcceptPolicyRequest(BaseModel):
    """Processing consent is recorded by calling the endpoint. This flag is the
    separate opportunity-alert opt-in, and stays false unless the person ticks it."""
    notify_opportunity_alerts: bool = False


class OpportunityAlertsRequest(BaseModel):
    enabled: bool


class NotificationPreferencesRequest(BaseModel):
    """Any of the three preferences. A field that is left out stays as it was,
    including "not chosen yet"; a field that is sent is recorded as chosen."""
    allow_tagging: bool | None = None
    preferred_post_type: str | None = Field(default=None, max_length=30)
    notify_opportunity_alerts: bool | None = None

    @field_validator("preferred_post_type")
    @classmethod
    def _post_type(cls, value: str | None) -> str | None:
        return _check_post_type(value)


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str   # encode as a QR code in the client


class MFACodeRequest(BaseModel):
    code: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class SimpleMessage(BaseModel):
    status: str
    reset_token: str | None = None   # returned only in non-production for testing


class RegisterResponse(BaseModel):
    user: UserResponse
    # Returned only outside production (no email-sending integration exists yet,
    # so this lets the verification flow be exercised in dev/test). In production
    # it is masked to None so a bare API response can never hand out a live,
    # unexpired auth token for someone else's account to a client that merely
    # guessed/observed their email address.
    email_verification_token: str | None = None
