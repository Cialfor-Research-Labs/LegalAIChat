from __future__ import annotations

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
