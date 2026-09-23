"""Password hashing and JWT token handling.

Passwords are hashed with Argon2 (never stored in plain text). Tokens are signed
JWTs used for access, refresh, and email verification.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.core.config import settings

_ph = PasswordHasher()
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


def _create_token(subject: str, token_type: str, expires_delta: timedelta, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def create_access_token(user_id: str, role: str, token_version: int = 0) -> str:
    return _create_token(
        user_id, "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        {"role": role, "tv": token_version},
    )


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                         {"tv": token_version})


def token_is_current(payload: dict, user) -> bool:
    """False once the user's token_version has moved past the one this token
    was issued under. Tokens minted before versioning existed carry no "tv"
    and count as version 0, so deploying this logs nobody out."""
    return int(payload.get("tv", 0)) == int(user.token_version or 0)


# A real Argon2 hash of a random throwaway string, verified against on logins
# for unknown emails so "no such account" takes as long as "wrong password"
# (otherwise response time alone reveals which emails are registered).
_DUMMY_HASH = _ph.hash("timing-equaliser-not-a-real-password")


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def create_email_verification_token(user_id: str) -> str:
    return _create_token(user_id, "email_verify", timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS))


def create_password_reset_token(user_id: str, token_version: int = 0) -> str:
    # Carries tv: a successful reset bumps the version, so each reset link
    # works exactly once (and any older unused link dies with it).
    return _create_token(user_id, "password_reset", timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS),
                         {"tv": token_version})


# ---- TOTP multi-factor authentication ----

def generate_mfa_secret() -> str:
    import pyotp
    return pyotp.random_base32()


def mfa_provisioning_uri(secret: str, email: str) -> str:
    import pyotp
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.MFA_ISSUER)


def verify_totp(secret: str | None, code: str | None) -> bool:
    if not secret or not code:
        return False
    import pyotp
    # valid_window=1 tolerates a 30s clock skew either side.
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decode and validate a JWT. Raises jwt exceptions on failure."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload
