"""
V1 Beta Authentication Router
==============================
Handles three V1-specific auth flows:

  POST /v1/auth/login          — Direct email/password login for V1 app users.
  GET  /v1/auth/launch-token   — (SSO path) Generate a short-lived launch token
                                  for an already-authenticated user from the main app.
  POST /v1/auth/exchange       — Exchange a launch token for a full V1 session token.
  GET  /v1/auth/status         — Feature-flag probe (is V1 enabled?).

All endpoints check V1_ENABLED.  Existing /auth/* routes are NOT modified.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ..db.db_client import db_client
from ..services.auth_service import (
    _V1_LAUNCH_TOKEN_MINUTES,
    create_access_token,
    create_v1_launch_token,
    decode_v1_launch_token,
    get_current_user,
)

router = APIRouter(prefix="/v1/auth", tags=["v1-auth"])


# ── Feature flag ─────────────────────────────────────────────────────────────

def _v1_enabled() -> bool:
    """Return True when V1_ENABLED env var is set to a truthy value.

    Defaults to True so V1 works out-of-the-box in development.
    Set V1_ENABLED=false / 0 / no / off to disable the entire V1 surface.
    """
    return os.getenv("V1_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _require_v1_enabled() -> None:
    """FastAPI dependency — raise 503 when V1 is disabled via feature flag."""
    if not _v1_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V1 Beta is currently disabled. Set V1_ENABLED=true to enable it.",
        )


# ── Request / Response models ─────────────────────────────────────────────────

class V1LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class V1LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str]


class V1LaunchTokenResponse(BaseModel):
    launch_token: str
    expires_in_seconds: int
    token_type: str = "v1_launch"


class V1ExchangeRequest(BaseModel):
    launch_token: str = Field(..., description="Short-lived V1 launch token to exchange.")


class V1ExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str]


class V1StatusResponse(BaseModel):
    v1_enabled: bool
    version: str = "1.0.0-beta"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status", response_model=V1StatusResponse)
async def v1_status():
    """
    Feature-flag probe.  The V1 frontend calls this on startup to decide
    whether to show the workspace or a 'coming soon' screen.
    No authentication required.
    """
    return V1StatusResponse(v1_enabled=_v1_enabled())


@router.post("/login", response_model=V1LoginResponse)
async def v1_login(
    request: V1LoginRequest,
    _: None = Depends(_require_v1_enabled),
):
    """
    Direct email/password login for the V1 application.

    Authenticates the user against the shared user store and issues a
    standard access token.  This is the primary entry-point when a user
    opens the V1 app directly (not via the SSO launcher from the main app).
    """
    user = db_client.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return V1LoginResponse(
        access_token=create_access_token(user["user_id"]),
        user=user,
    )


@router.get("/launch-token", response_model=V1LaunchTokenResponse)
async def generate_v1_launch_token(
    current_user: dict[str, Any] = Depends(get_current_user),
    _: None = Depends(_require_v1_enabled),
):
    """
    SSO path — generate a short-lived V1 launch token for an already
    authenticated user.

    Called by the existing Vidhi AI application when the user clicks
    'Open V1.0 Beta'. Requires a valid Bearer access token from the main
    app. The returned launch token is valid for 5 minutes and must be
    exchanged via POST /v1/auth/exchange before it expires.
    """
    launch_token = create_v1_launch_token(current_user["user_id"])
    return V1LaunchTokenResponse(
        launch_token=launch_token,
        expires_in_seconds=_V1_LAUNCH_TOKEN_MINUTES * 60,
    )


@router.post("/exchange", response_model=V1ExchangeResponse)
async def exchange_v1_launch_token(
    request: V1ExchangeRequest,
    _: None = Depends(_require_v1_enabled),
):
    """
    Exchange a V1 launch token for a full session access token.

    This is the second step of the SSO launcher flow:
      1. Main app calls GET /v1/auth/launch-token  → launch_token (5 min)
      2. V1 app opens, receives launch_token (via URL param or postMessage)
      3. V1 app calls POST /v1/auth/exchange       → access_token (full session)

    Validates signature, scope, and expiry. Expired or tampered tokens are
    rejected with 401.  On success returns a standard access token identical
    in format to the one issued by POST /auth/login.
    """
    token_payload = decode_v1_launch_token(request.launch_token)
    user_id = token_payload["user_id"]

    user = db_client.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )

    return V1ExchangeResponse(
        access_token=create_access_token(user_id),
        user=user,
    )
