"""
Structured request, response, state, and context models for Agent Orchestration.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentRunState(str, Enum):
    CREATED = "created"
    CONTEXT_READY = "context_ready"
    RETRIEVING = "retrieving"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    REVIEW_REQUIRED = "review_required"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentCommand(str, Enum):
    RESEARCH = "/research"
    NEXT = "/next"
    TIMELINE = "/timeline"
    DRAFT = "/draft"
    REVIEW = "/review"
    BRIEF = "/brief"
    DIARY = "/diary"


class MatterContext(BaseModel):
    matter_id: str
    user_id: str
    title: str
    description: str = ""
    case_number: str | None = None
    court: str | None = None
    stage: str | None = None
    status: str = "open"
    parties: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_hearings: list[dict[str, Any]] = Field(default_factory=list)
    open_tasks: list[dict[str, Any]] = Field(default_factory=list)
    recent_timeline_events: list[dict[str, Any]] = Field(default_factory=list)
    selected_documents: list[dict[str, Any]] = Field(default_factory=list)
    previous_verified_research: list[dict[str, Any]] = Field(default_factory=list)
    compact_conversation_summary: str = ""
    estimated_tokens: int = 0


class AgentRunRequest(BaseModel):
    command_text: str = Field(..., description="Slash command with optional query, e.g. '/research Find cases under Sec 138'")
    conversation_history: list[dict[str, Any]] = Field(default_factory=list, description="Recent user/assistant chat history")


class ToolCallRecord(BaseModel):
    tool_call_id: str
    tool_name: str
    status: str = "started"
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    error_text: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class AgentRunResponse(BaseModel):
    agent_run_id: str
    user_id: str
    matter_id: str
    command: str
    status: AgentRunState
    output_text: str | None = None
    error_text: str | None = None
    token_count: int = 0
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
