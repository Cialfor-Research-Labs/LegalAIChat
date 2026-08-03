"""
Matter context collection service with ownership validation and token limit enforcement.
"""

from __future__ import annotations

import logging
from typing import Any

from ..db.db_client import db_client
from .agent_models import MatterContext

logger = logging.getLogger("tllac.services.matter_context_service")


def estimate_tokens(text: str | dict | list) -> int:
    """Rough estimation of token count (approx. 4 characters per token)."""
    if isinstance(text, (dict, list)):
        text = str(text)
    return max(1, len(str(text)) // 4)


class MatterContextService:
    """Service to assemble matter context after verifying user ownership."""

    def __init__(self, max_context_tokens: int = 3000):
        self.max_context_tokens = max_context_tokens

    def build_matter_context(
        self,
        user_id: str,
        matter_id: str,
        conversation_history: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> MatterContext:
        """
        Validates matter ownership and constructs a token-budgeted MatterContext object.
        Raises ValueError if matter does not exist or user does not own the matter.
        """
        token_limit = max_tokens or self.max_context_tokens

        # 1. Strict Ownership Validation FIRST
        # Raises ValueError if matter does not exist or does not belong to user_id
        matter_row = db_client.get_matter(user_id, matter_id)

        # 2. Collect Matter Components
        title = matter_row.get("title", "")
        description = matter_row.get("description", "")
        case_number = matter_row.get("case_number")
        court = matter_row.get("court")
        stage = matter_row.get("stage")
        status = matter_row.get("status", "open")

        # Parties & Counsel
        parties = db_client.list_matter_parties(user_id, matter_id)

        # Upcoming Hearings
        all_hearings = db_client.list_matter_hearings(user_id, matter_id)
        upcoming_hearings = [
            h for h in all_hearings
            if h.get("status") in ("scheduled", "upcoming", "open")
        ]

        # Open Tasks
        all_tasks = db_client.list_matter_tasks(user_id, matter_id)
        open_tasks = [
            t for t in all_tasks
            if t.get("status") not in ("completed", "done", "cancelled")
        ]

        # Recent Timeline Events
        recent_events = db_client.list_matter_events(user_id, matter_id)[:10]

        # Selected Documents (Truncating extracted_text if needed)
        docs = db_client.list_matter_documents(user_id, matter_id)[:5]
        if not docs:
            logger.info("No uploaded matter documents found for matter '%s' while building context.", matter_id)
        selected_documents = []
        for doc in docs:
            extracted = doc.get("extracted_text") or ""
            if len(extracted) > 500:
                extracted = extracted[:500] + "... [truncated]"
            selected_documents.append({
                "document_id": doc.get("document_id"),
                "title": doc.get("title"),
                "file_name": doc.get("file_name"),
                "extracted_text_preview": extracted,
            })

        # Previous Verified Research
        all_research = db_client.list_matter_research(user_id, matter_id)
        verified_research = [
            {
                "research_id": r.get("research_id"),
                "title": r.get("title"),
                "query": r.get("query"),
                "content_preview": (r.get("content") or "")[:300],
            }
            for r in all_research
            if r.get("verification_status") in ("verified", "approved")
        ][:5]

        # Compact Conversation Summary (Truncate older history to fit remaining token budget)
        compact_summary = self._truncate_conversation_history(
            conversation_history or [],
            max_history_tokens=1000,
        )

        context = MatterContext(
            matter_id=matter_id,
            user_id=user_id,
            title=title,
            description=description,
            case_number=case_number,
            court=court,
            stage=stage,
            status=status,
            parties=parties,
            upcoming_hearings=upcoming_hearings,
            open_tasks=open_tasks,
            recent_timeline_events=recent_events,
            selected_documents=selected_documents,
            previous_verified_research=verified_research,
            compact_conversation_summary=compact_summary,
            estimated_tokens=0,
        )

        # Estimate total tokens and trim components if exceeding limit
        context_dict = context.model_dump()
        total_tokens = estimate_tokens(context_dict)
        
        if total_tokens > token_limit:
            logger.info(
                f"Context tokens ({total_tokens}) exceed budget ({token_limit}). Truncating events and research."
            )
            context.recent_timeline_events = context.recent_timeline_events[:5]
            context.previous_verified_research = context.previous_verified_research[:2]
            context.compact_conversation_summary = compact_summary[:500]
            total_tokens = estimate_tokens(context.model_dump())

        context.estimated_tokens = total_tokens
        return context

    def _truncate_conversation_history(
        self,
        history: list[dict[str, Any]],
        max_history_tokens: int = 1000,
    ) -> str:
        """Truncates older conversation messages to fit within token limit."""
        if not history:
            return ""

        summary_lines = []
        # Process from newest to oldest
        total_est = 0
        for msg in reversed(history):
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            line = f"{role.upper()}: {content}"
            est = estimate_tokens(line)
            if total_est + est > max_history_tokens:
                break
            summary_lines.append(line)
            total_est += est

        # Re-reverse to maintain chronological order
        return "\n".join(reversed(summary_lines))


matter_context_service = MatterContextService()
