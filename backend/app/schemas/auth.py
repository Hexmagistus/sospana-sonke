"""Request/response schemas for authentication."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    mobile_number: str | None = Field(default=None, max_length=30)


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


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    mobile_number: str | None
    email_verified: bool
    mfa_enabled: bool
    role: str


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
    # In production this token is emailed to the user; in development it is
    # returned directly so the flow can be exercised without an email provider.
    email_verification_token: str
