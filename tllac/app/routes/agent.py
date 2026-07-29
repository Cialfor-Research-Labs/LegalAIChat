"""
Agent Orchestration API router.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from ..db.db_client import db_client
from ..services.agent_models import AgentRunRequest, AgentRunResponse
from ..services.agent_orchestrator import agent_orchestrator
from ..services.auth_service import get_current_user

router = APIRouter(prefix="/v1/matters/{matter_id}/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
async def run_agent_command(
    matter_id: str,
    request: AgentRunRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Triggers an agent command for a matter.
    Enforces ownership validation, deterministic routing, and context limits.
    """
    user_id = current_user["user_id"]
    try:
        response = agent_orchestrator.run_agent(
            user_id=user_id,
            matter_id=matter_id,
            raw_input=request.command_text,
            conversation_history=request.conversation_history,
        )
        if response.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.error_text or "Agent run failed.",
            )
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal agent execution error: {ex}",
        )


@router.get("/runs")
async def list_agent_runs(
    matter_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """List all agent runs for a matter."""
    user_id = current_user["user_id"]
    try:
        db_client.get_matter(user_id, matter_id)
        if db_client._backend != "postgres":
            runs = [
                r for r in db_client._memory_v1_tables["agent_runs"].values()
                if r["user_id"] == user_id and r["matter_id"] == matter_id
            ]
            runs.sort(key=lambda item: item["created_at"], reverse=True)
            return runs
        with db_client._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM agent_runs WHERE user_id = %s AND matter_id = %s ORDER BY created_at DESC",
                    (user_id, matter_id),
                )
                return cur.fetchall()
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.get("/runs/{agent_run_id}")
async def get_agent_run_details(
    matter_id: str,
    agent_run_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get detailed agent run execution record with tool calls."""
    user_id = current_user["user_id"]
    try:
        run_record = db_client.get_agent_run(user_id, matter_id, agent_run_id)
        tool_calls = []
        if db_client._backend != "postgres":
            tool_calls = [
                tc for tc in db_client._memory_v1_tables["agent_tool_calls"].values()
                if tc["user_id"] == user_id and tc["matter_id"] == matter_id and tc["agent_run_id"] == agent_run_id
            ]
        else:
            with db_client._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM agent_tool_calls WHERE user_id = %s AND matter_id = %s AND agent_run_id = %s ORDER BY created_at",
                        (user_id, matter_id, agent_run_id),
                    )
                    tool_calls = cur.fetchall()
        return {**run_record, "tool_calls": tool_calls}
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
