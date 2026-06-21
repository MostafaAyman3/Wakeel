"""
Authentication API router.

MVP demo auth: a single shared demo password issues a JWT for the support
agent / customer roles. This is intentionally minimal so the M3 demo works
end-to-end. Replace with a real user store + password hashing post-MVP.

Endpoint: POST /api/v1/auth/login  →  { access_token, token_type, role, email }
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import create_access_token
from backend.core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = get_logger(__name__)

# MVP-only shared demo password. NOT for production.
_DEMO_PASSWORD = "demo1234"
_ALLOWED_ROLES = {"agent", "customer", "supervisor"}


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=1, max_length=200)
    role: str = Field(default="agent")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    """Issue a JWT for a valid demo login.

    MVP rule: any email + the shared demo password is accepted. The role is
    embedded in the token so the frontend can show the right view.
    """
    if req.password != _DEMO_PASSWORD:
        logger.warning("login_rejected", email=req.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    role = req.role if req.role in _ALLOWED_ROLES else "agent"
    token = create_access_token(user_id=req.email, email=req.email, role=role)
    logger.info("login_ok", email=req.email, role=role)
    return LoginResponse(access_token=token, role=role, email=req.email)
