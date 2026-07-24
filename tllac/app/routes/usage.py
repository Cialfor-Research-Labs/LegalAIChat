"""
Token usage statistics route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..db.db_client import db_client
from ..services.auth_service import get_current_user

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats")
async def get_usage_stats(
    current_user: dict[str, str] = Depends(get_current_user),
):
    """Return token usage statistics for the authenticated user for today (UTC)."""
    return db_client.get_token_usage(current_user["user_id"])
