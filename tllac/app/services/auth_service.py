from __future__ import annotations

# V1 launch token lifetime (minutes).  Keep short — exchange immediately.
_V1_LAUNCH_TOKEN_MINUTES: int = 5
_V1_TOKEN_SCOPE: str = "v1_launch"

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Header, HTTPException, status

from ..db.db_client import db_client

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / "tllac" / ".env")


def _secret_key() -> bytes:
    secret = os.getenv("APP_SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("APP_SECRET_KEY is required for authentication.")
    return secret.encode("utf-8")


def _urlsafe_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("utf-8")


def _urlsafe_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=int(os.getenv("AUTH_TOKEN_HOURS", "24"))
    )
    payload = {
        "user_id": user_id,
        "exp": int(expires_at.timestamp()),
    }
    payload_segment = _urlsafe_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        _secret_key(),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_segment}.{_urlsafe_encode(signature)}"


def decode_access_token(token: str) -> dict[str, str]:
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    expected_signature = hmac.new(
        _secret_key(),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = _urlsafe_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    payload = json.loads(_urlsafe_decode(payload_segment))
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
        )

    user_id = str(payload.get("user_id", "")).strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    return {"user_id": user_id}


# ── V1 launch-token helpers ──────────────────────────────────────────────────

def create_v1_launch_token(user_id: str) -> str:
    """Return a short-lived, scope-limited token for V1 Beta launch.

    The token is valid for ``_V1_LAUNCH_TOKEN_MINUTES`` minutes and carries a
    ``scope`` claim of ``v1_launch`` so it can never be misused as a regular
    access token.  Signed with the same APP_SECRET_KEY / HMAC-SHA256 scheme
    as the main access token — no new dependencies.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_V1_LAUNCH_TOKEN_MINUTES)
    payload = {
        "user_id": user_id,
        "scope": _V1_TOKEN_SCOPE,
        "exp": int(expires_at.timestamp()),
    }
    payload_segment = _urlsafe_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        _secret_key(),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_segment}.{_urlsafe_encode(signature)}"


def decode_v1_launch_token(token: str) -> dict[str, str]:
    """Validate a V1 launch token and return ``{"user_id": ...}``.

    Raises HTTP 401 if the token is malformed, has an invalid signature,
    has expired, or carries the wrong scope.
    """
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid V1 launch token.",
        ) from exc

    expected_signature = hmac.new(
        _secret_key(),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = _urlsafe_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid V1 launch token.",
        )

    payload = json.loads(_urlsafe_decode(payload_segment))

    if payload.get("scope") != _V1_TOKEN_SCOPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a V1 launch token.",
        )

    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="V1 launch token has expired.",
        )

    user_id = str(payload.get("user_id", "")).strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid V1 launch token.",
        )
    return {"user_id": user_id}


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    user = db_client.get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )
    return user
