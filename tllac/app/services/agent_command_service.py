from __future__ import annotations

from dataclasses import dataclass
import difflib
import os
import re
from pathlib import Path
from typing import Any

from ..db.db_client import db_client
from .document_generator_service import generate_document
from .matter_context_service import matter_context_service


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILLS_ROOT = _REPO_ROOT / "document-generator-skills"


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def advanced_commands_enabled() -> bool:
    # Case Agent commands are expected to work by default in the V1 workspace.
    # An explicit "false" environment flag can still disable them for deployments
    # that need to keep the advanced workflows gated.
    return _env_flag("ADVANCED_AGENT_COMMANDS_ENABLED", True)


def command_enabled(command: str) -> bool:
    if command in {"/research", "/next", "/timeline"}:
        return True
    return advanced_commands_enabled()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _verified_research_sources(user_id: str, matter_id: str) -> list[dict[str, Any]]:
    return [
        research
        for research in db_client.list_matter_research(user_id, matter_id)
        if str(research.get("verification_status") or "").lower() == "verified"
    ]


def _research_context_block(user_id: str, matter_id: str) -> str:
    verified = _verified_research_sources(user_id, matter_id)
    if not verified:
        return ""
    lines = ["Verified research sources:"]
    for research in verified:
        lines.append(f"- {research.get('title', 'Research')} :: {research.get('content', '')[:600]}")
    return "\n".join(lines)


def build_next_preview(user_id: str, matter_id: str) -> dict[str, Any]:
    context = matter_context_service.build_matter_context(user_id, matter_id, conversation_history=[], max_tokens=2500)
    hearings = context.upcoming_hearings[:5]
    tasks = context.open_tasks[:8]
    timeline = context.recent_timeline_events[:8]
    documents = context.selected_documents[:5]
    return {
        "matter_id": matter_id,
        "title": context.title,
        "hearings": hearings,
        "deadlines": [
            {
                "title": task.get("title"),
                "due_at": task.get("due_at"),
                "priority": task.get("priority"),
            }
            for task in tasks
            if task.get("due_at")
        ],
        "tasks": tasks,
        "recent_events": timeline,
        "documents": documents,
        "read_only": True,
    }


def build_timeline_preview(user_id: str, matter_id: str) -> dict[str, Any]:
    matter = db_client.get_matter(user_id, matter_id)
    return {
        "matter_id": matter_id,
        "title": matter.get("title", ""),
        "events": db_client.list_matter_events(user_id, matter_id),
        "hearings": db_client.list_matter_hearings(user_id, matter_id),
        "tasks": db_client.list_matter_tasks(user_id, matter_id),
        "notes": db_client.list_matter_notes(user_id, matter_id),
        "documents": db_client.list_matter_documents(user_id, matter_id),
        "read_only": True,
    }


def build_review_report(
    user_id: str,
    matter_id: str,
    *,
    source_type: str,
    source_id: str,
    query: str = "",
) -> dict[str, Any]:
    source_type = source_type.strip().lower()
    issues: list[str] = []
    missing_information: list[str] = []
    conflicting_facts: list[str] = []
    source_references: list[dict[str, Any]] = []

    if source_type == "document":
        document = db_client.get_matter_related_record(
            kind="document",
            user_id=user_id,
            matter_id=matter_id,
            record_id=source_id,
            include_archived=True,
        )
        text = str(document.get("extracted_text") or "")
        for token in ("section", "date", "signature", "witness", "amount", "notice", "payment"):
            if token not in text.lower():
                missing_information.append(f"Document does not clearly show {token}.")
        if "not" in text.lower() and "yes" in query.lower():
            conflicting_facts.append("Query and document text appear to diverge on an important point.")
        source_references.append({"source_type": "document", "source_id": source_id, "title": document.get("title", "")})
    else:
        research = next(
            (row for row in db_client.list_matter_research(user_id, matter_id) if row.get("research_id") == source_id),
            None,
        )
        if research:
            source_references.append({"source_type": "research", "source_id": source_id, "title": research.get("title", "")})
            content = str(research.get("content") or "")
            if "section" not in content.lower():
                missing_information.append("Verified research does not cite a section explicitly.")
        else:
            issues.append("No review target found.")

    if query:
        issues.append(_normalize(query))

    return {
        "matter_id": matter_id,
        "source_type": source_type,
        "source_id": source_id,
        "identified_issues": issues,
        "missing_information": missing_information,
        "conflicting_facts": conflicting_facts,
        "source_references": source_references,
        "read_only": True,
    }


def build_brief_preview(user_id: str, matter_id: str) -> dict[str, Any]:
    context = matter_context_service.build_matter_context(user_id, matter_id, conversation_history=[], max_tokens=2500)
    next_hearing = context.upcoming_hearings[0] if context.upcoming_hearings else None
    verified_research = _verified_research_sources(user_id, matter_id)
    recent_orders = [
        event for event in context.recent_timeline_events
        if _normalize(str(event.get("event_type") or "")).lower() in {"order", "judgment", "direction", "ruling"}
    ]
    open_tasks = context.open_tasks[:8]
    brief_text = "\n".join(
        [
            f"Matter: {context.title}",
            f"Next hearing: {next_hearing.get('title')} on {next_hearing.get('hearing_at')}" if next_hearing else "Next hearing: none scheduled",
            f"Open tasks: {len(open_tasks)}",
            f"Recent orders: {len(recent_orders)}",
            f"Verified research memos: {len(verified_research)}",
        ]
    )
    return {
        "matter_id": matter_id,
        "title": f"Brief for {context.title}",
        "next_hearing": next_hearing,
        "open_tasks": open_tasks,
        "recent_orders": recent_orders,
        "verified_research": verified_research,
        "brief_text": brief_text,
        "read_only": False,
    }


def build_draft_preview(
    user_id: str,
    matter_id: str,
    *,
    document_type: str,
    document_type_label: str,
    case_details: str,
    party_details: str = "",
    recipient_details: str = "",
    relevant_info: str = "",
    additional_info: str = "",
    structured_fields: dict[str, str] | None = None,
    structured_sections: list[dict[str, object]] | None = None,
    skill_name: str = "",
    skill_prompt: str = "",
) -> tuple[str, int]:
    research_context = _research_context_block(user_id, matter_id)
    combined_case_details = "\n\n".join(part for part in (case_details, research_context) if part).strip()
    return generate_document(
        document_type=document_type,
        document_type_label=document_type_label,
        party_details=party_details,
        recipient_details=recipient_details,
        case_details=combined_case_details,
        relevant_info=relevant_info,
        additional_info=additional_info,
        structured_fields=structured_fields,
        structured_sections=structured_sections,
        skill_name=skill_name,
        skill_prompt=skill_prompt,
    )


def compare_text_versions(left: str, right: str) -> str:
    diff = difflib.unified_diff(
        left.splitlines(),
        right.splitlines(),
        fromfile="version_a",
        tofile="version_b",
        lineterm="",
    )
    return "\n".join(diff)
