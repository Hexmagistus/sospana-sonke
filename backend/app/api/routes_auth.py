"""Authentication routes (blueprint Step 1)."""
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import security
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.schemas.auth import (
    RegisterRequest, RegisterResponse, LoginRequest, TokenResponse,
    RefreshRequest, UserResponse, MFASetupResponse, MFACodeRequest,
    PasswordResetRequest, PasswordResetConfirm, SimpleMessage,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    user = User(
        email=email,
        password_hash=security.hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        mobile_number=body.mobile_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_email_verification_token(user.id)
    return RegisterResponse(user=UserResponse.model_validate(user), email_verification_token=token)


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = security.decode_token(token, expected_type="email_verify")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token.")
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.email_verified = True
    db.commit()
    return {"status": "verified", "email": user.email}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    # Constant-ish response regardless of which check fails, to avoid user enumeration.
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")
    if user.mfa_enabled:
        if not security.verify_totp(user.mfa_secret, body.otp_code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="MFA code required or invalid.")
    return TokenResponse(
        access_token=security.create_access_token(user.id, user.role),
        refresh_token=security.create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = security.decode_token(body.refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    return TokenResponse(
        access_token=security.create_access_token(user.id, user.role),
        refresh_token=security.create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


# ---- MFA (TOTP) ----

@router.post("/mfa/setup", response_model=MFASetupResponse)
def mfa_setup(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Generate (or regenerate) a TOTP secret. MFA is not active until confirmed."""
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is already enabled.")
    secret = security.generate_mfa_secret()
    user.mfa_secret = secret
    db.commit()
    return MFASetupResponse(secret=secret, otpauth_uri=security.mfa_provisioning_uri(secret, user.email))


@router.post("/mfa/enable", response_model=UserResponse)
def mfa_enable(body: MFACodeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start MFA setup first.")
    if not security.verify_totp(user.mfa_secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code.")
    user.mfa_enabled = True
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/mfa/disable", response_model=UserResponse)
def mfa_disable(body: MFACodeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA is not enabled.")
    if not security.verify_totp(user.mfa_secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code.")
    user.mfa_enabled = False
    user.mfa_secret = None
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


# ---- Password reset ----

@router.post("/password-reset/request", response_model=SimpleMessage)
def password_reset_request(body: PasswordResetRequest, db: Session = Depends(get_db)):
    """Always returns success (no account enumeration). Emails a reset link if the
    account exists; in non-production the token is returned for testing."""
    user = db.query(User).filter(User.email == body.email.lower()).first()
    token = None
    if user:
        token = security.create_password_reset_token(user.id)
        try:
            from app.notifications.email import get_email_provider
            get_email_provider().send(user.email, "Reset your Sospana Sonke password",
                                      f"Use this token to reset your password: {token}")
        except Exception:
            pass
    return SimpleMessage(status="If that email exists, a reset link has been sent.",
                         reset_token=token if settings.ENV != "production" else None)


@router.post("/password-reset/confirm", response_model=SimpleMessage)
def password_reset_confirm(body: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        payload = security.decode_token(body.token, expected_type="password_reset")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.password_hash = security.hash_password(body.new_password)
    db.commit()
    return SimpleMessage(status="Password updated. Please sign in with your new password.")
