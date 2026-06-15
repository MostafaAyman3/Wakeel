"""
JWT authentication — token creation, verification, and user context.

Provides:
- create_access_token()  : generate a signed JWT for a user
- verify_token()         : decode and validate a token, return payload
- get_current_user()     : FastAPI dependency for protected routes

All agent requests carry user context extracted from the JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from backend.core.config import get_settings
from backend.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=True)


class TokenPayload(BaseModel):
    sub: str                  # user_id
    email: str
    role: str = "user"
    permissions: list[str] = Field(default_factory=lambda: ["read"])
    exp: datetime


class UserContext(BaseModel):
    user_id: str
    email: str
    role: str
    permissions: list[str] = Field(default_factory=lambda: ["read"])


def create_access_token(
    user_id: str,
    email: str,
    role: str = "user",
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: Unique user identifier (UUID string).
        email: User email address.
        role: User role — default 'user'.
        expires_delta: Custom expiry override. Defaults to ACCESS_TOKEN_EXPIRE_HOURS.

    Returns:
        Encoded JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.access_token_expire_hours)

    now = datetime.now(tz=timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    logger.debug("access_token_created", user_id=user_id, role=role)
    return token


def verify_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Raises:
        HTTPException 401 if token is invalid or expired.
    """
    try:
        raw = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**raw)
    except JWTError as exc:
        logger.warning("token_verification_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> UserContext:
    """
    FastAPI dependency — extracts and validates user from Bearer token.

    Usage:
        @router.get("/protected")
        async def protected(user: UserContext = Depends(get_current_user)):
            ...
    """
    payload = verify_token(credentials.credentials)
    return UserContext(
        user_id=payload.sub,
        email=payload.email,
        role=payload.role,
        permissions=payload.permissions,
    )
