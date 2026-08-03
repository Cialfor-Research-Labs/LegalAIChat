"""
Registry of strictly approved agent tools.
Unapproved tool invocation requests are rejected.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from ..db.db_client import db_client
from .legal_rag_service import build_legal_rag_context_from_result, retrieve_legal_rag_result

logger = logging.getLogger("tllac.services.agent_tools")


# --- Approved Tool Implementation Functions ---

def get_matter_tool(user_id: str, matter_id: str, **kwargs: Any) -> dict[str, Any]:
    """Retrieve matter details."""
    return db_client.get_matter(user_id, matter_id)


def get_parties_tool(user_id: str, matter_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    """Retrieve matter parties."""
    return db_client.list_matter_parties(user_id, matter_id)


def get_hearings_tool(user_id: str, matter_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    """Retrieve matter hearings."""
    return db_client.list_matter_hearings(user_id, matter_id)


def get_tasks_tool(user_id: str, matter_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    """Retrieve matter tasks."""
    return db_client.list_matter_tasks(user_id, matter_id)


def search_matter_documents_tool(user_id: str, matter_id: str, query: str = "", **kwargs: Any) -> list[dict[str, Any]]:
    """Search uploaded matter documents for query terms."""
    docs = db_client.list_matter_documents(user_id, matter_id)
    if not query:
        return docs
    query_lower = query.lower()
    results = []
    for doc in docs:
        text = (doc.get("extracted_text") or "").lower()
        title = (doc.get("title") or "").lower()
        if query_lower in text or query_lower in title:
            results.append(doc)
    return results


def search_legal_corpus_tool(query: str = "", **kwargs: Any) -> dict[str, Any]:
    """Search statutes and case-law corpus via Legal RAG service."""
    if not query:
        return {"statute_matches": [], "case_matches": [], "context_block": ""}
    rag_res = retrieve_legal_rag_result(query)
    return {
        "query": query,
        "statute_matches": [
            {
                "authority_type": auth.authority_type,
                "title": auth.title,
                "reference": auth.reference,
                "summary": auth.summary,
                "score": auth.score,
            }
            for auth in rag_res.statute_matches
        ],
        "case_matches": [
            {
                "authority_type": auth.authority_type,
                "title": auth.title,
                "reference": auth.reference,
                "summary": auth.summary,
                "score": auth.score,
            }
            for auth in rag_res.case_matches
        ],
        "context_block": build_legal_rag_context_from_result(rag_res),
        "confidence": rag_res.confidence,
    }


def save_research_tool(
    user_id: str,
    matter_id: str,
    title: str = "Agent Research Note",
    query: str = "",
    content: str = "",
    evidence: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Save verified legal research to matter research store."""
    return db_client.create_matter_research(
        user_id=user_id,
        matter_id=matter_id,
        title=title,
        query=query,
        content=content,
        evidence=evidence or [],
        verification_status="verified",
    )


def save_draft_version_tool(
    user_id: str,
    matter_id: str,
    content: str = "",
    draft_id: str | None = None,
    citations: list[dict[str, Any]] | None = None,
    title: str = "Agent Legal Draft",
    document_type: str = "legal_notice",
    **kwargs: Any,
) -> dict[str, Any]:
    """Save new version of a matter draft."""
    if not draft_id:
        # Check if draft already exists or create new matter draft parent record
        drafts = db_client.list_matter_drafts(user_id, matter_id)
        if drafts:
            draft_id = drafts[0]["draft_id"]
        else:
            draft_rec = db_client.create_matter_draft(
                user_id=user_id,
                matter_id=matter_id,
                title=title,
                document_type=document_type,
            )
            draft_id = draft_rec["draft_id"]

    return db_client.create_draft_version(
        user_id=user_id,
        matter_id=matter_id,
        draft_id=draft_id,
        content=content,
        citations=citations or [],
    )


def save_timeline_tool(
    user_id: str,
    matter_id: str,
    event_type: str = "milestone",
    title: str = "Timeline Event",
    description: str = "",
    event_at: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Add a new timeline event to the matter."""
    return db_client.create_matter_event(
        user_id=user_id,
        matter_id=matter_id,
        event_type=event_type,
        title=title,
        description=description,
        event_at=event_at,
    )


def create_draft_diary_or_task_entry_tool(
    user_id: str,
    matter_id: str,
    title: str = "New Task",
    description: str = "",
    due_at: str | None = None,
    entry_type: str = "task",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a task or hearing entry in matter diary."""
    if entry_type == "hearing":
        return db_client.create_matter_hearing(
            user_id=user_id,
            matter_id=matter_id,
            title=title,
            hearing_at=due_at,
            notes=description,
        )
    return db_client.create_matter_task(
        user_id=user_id,
        matter_id=matter_id,
        title=title,
        description=description,
        due_at=due_at,
    )


# --- Tool Registry Mapping ---

APPROVED_TOOLS: dict[str, Callable[..., Any]] = {
    "get_matter": get_matter_tool,
    "get_parties": get_parties_tool,
    "get_hearings": get_hearings_tool,
    "get_tasks": get_tasks_tool,
    "search_matter_documents": search_matter_documents_tool,
    "search_legal_corpus": search_legal_corpus_tool,
    "save_research": save_research_tool,
    "save_draft_version": save_draft_version_tool,
    "save_timeline": save_timeline_tool,
    "create_draft_diary_or_task_entry": create_draft_diary_or_task_entry_tool,
}

# Also support canonical human labels from prompt
_LABEL_MAPPING = {
    "get matter": "get_matter",
    "get parties": "get_parties",
    "get hearings": "get_hearings",
    "get tasks": "get_tasks",
    "search matter documents": "search_matter_documents",
    "search legal corpus": "search_legal_corpus",
    "save research": "save_research",
    "save draft version": "save_draft_version",
    "save timeline": "save_timeline",
    "create draft diary or task entry": "create_draft_diary_or_task_entry",
}


def normalize_tool_name(tool_name: str) -> str:
    cleaned = tool_name.strip().lower().replace("-", "_")
    return _LABEL_MAPPING.get(cleaned, cleaned)


def execute_approved_tool(
    tool_name: str,
    arguments: dict[str, Any],
    user_id: str,
    matter_id: str,
) -> Any:
    """
    Executes an approved tool after verifying it is in the registry.
    Raises ValueError if tool is not approved.
    """
    norm_name = normalize_tool_name(tool_name)
    if norm_name not in APPROVED_TOOLS:
        logger.error(f"Attempted execution of unapproved tool: '{tool_name}'")
        raise ValueError(
            f"Tool '{tool_name}' is not in the approved tool registry. "
            f"Approved tools are: {list(APPROVED_TOOLS.keys())}"
        )

    tool_func = APPROVED_TOOLS[norm_name]
    logger.info(f"Executing approved tool '{norm_name}' for user '{user_id}' matter '{matter_id}'")
    return tool_func(user_id=user_id, matter_id=matter_id, **arguments)
