"""Shared FastAPI dependencies: current-user resolution and role gating."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import decode_token, token_is_current
from app.db.session import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(creds.credentials, expected_type="access")
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise cred_exc
    if not user_id:
        raise cred_exc
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise cred_exc
    if not token_is_current(payload, user):
        raise cred_exc
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


_bearer_optional = HTTPBearer(auto_error=False)


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """The signed-in user, or None for anonymous visitors (never raises)."""
    if creds is None:
        return None
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except jwt.PyJWTError:
        return None
    user = db.get(User, payload.get("sub")) if payload.get("sub") else None
    if user is None or not user.is_active or user.deleted_at is not None:
        return None
    if not token_is_current(payload, user):
        return None
    return user
