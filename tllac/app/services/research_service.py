from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import os
import re
from typing import Any

from ..db.db_client import db_client
from .bedrock_llm_service import generate_notice_response
from .citation_verifier import (
    EvidenceSource,
    ResearchDraft,
    VerificationResult,
    parse_research_draft,
    verify_research_draft,
)
from .legal_rag_service import RetrievedAuthority, retrieve_legal_rag_result
from .matter_context_service import matter_context_service
from .matter_document_service import search_documents
from .online_legal_research import search_indiakanoon
from .research_planner import ResearchPlan, build_research_plan


logger = logging.getLogger("tllac.services.research_service")


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _stable_source_id(prefix: str, *parts: str) -> str:
    material = "|".join(_normalize(part) for part in parts if part is not None)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _safe_excerpt(text: str, limit: int = 600) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3].rstrip()}..."


def _format_citation(authority: RetrievedAuthority) -> str:
    parts = [authority.title.strip(), authority.reference.strip()]
    return " - ".join(part for part in parts if part)


def _plan_to_query_list(plan: ResearchPlan) -> list[tuple[str, str]]:
    return [
        *[("issue", query) for query in plan.issue_queries],
        *[("statute", query) for query in plan.statute_queries],
        *[("section", query) for query in plan.section_queries],
        *[("judgment", query) for query in plan.judgment_queries],
        *[("contrary", query) for query in plan.contrary_queries],
    ]


def _dedupe_sources(sources: list[EvidenceSource]) -> list[EvidenceSource]:
    ordered: list[EvidenceSource] = []
    seen: set[str] = set()
    for source in sources:
        if source.source_id in seen:
            continue
        seen.add(source.source_id)
        ordered.append(source)
    return ordered


def _build_legal_source(authority: RetrievedAuthority, *, query_kind: str) -> EvidenceSource:
    source_type = f"legal-{authority.authority_type}"
    citation = _format_citation(authority)
    court = ""
    date = ""
    if authority.authority_type == "case":
        court = authority.reference.split("(", 1)[0].strip()
        match = re.search(r"\(([^)]+)\)", authority.reference)
        date = match.group(1).strip() if match else ""

    source_id = _stable_source_id(
        "LC",
        authority.authority_type,
        authority.title,
        authority.reference,
        authority.source_file,
    )
    return EvidenceSource(
        source_id=source_id,
        source_type=source_type,
        title=authority.title,
        citation=citation,
        court=court,
        date=date,
        section=authority.reference if authority.authority_type == "statute" else "",
        page="",
        paragraph="",
        url="",
        extracted_text=authority.summary,
        metadata={
            "score": authority.score,
            "source_file": authority.source_file,
            "query_kind": query_kind,
            "verified": authority.verified,
        },
    )


def _build_document_source(document: dict[str, Any], hit: dict[str, Any], *, query_kind: str) -> EvidenceSource:
    document_id = str(hit.get("document_id") or document.get("document_id") or "")
    chunk_position = str(hit.get("chunk_position") or "")
    source_id = _stable_source_id(
        "MD",
        document_id,
        chunk_position,
        str(hit.get("page_number") or ""),
        str(hit.get("paragraph_number") or ""),
        str(document.get("original_filename") or ""),
    )
    page = f"page:{hit['page_number']}" if hit.get("page_number") is not None else ""
    paragraph = f"paragraph:{hit['paragraph_number']}" if hit.get("paragraph_number") is not None else ""
    return EvidenceSource(
        source_id=source_id,
        source_type="matter-document",
        title=str(document.get("original_filename") or document.get("title") or "Matter document"),
        citation=str(document.get("original_filename") or document.get("title") or ""),
        court="",
        date=str(document.get("upload_timestamp") or ""),
        section="",
        page=page,
        paragraph=paragraph,
        url=str(document.get("storage_path") or ""),
        extracted_text=_safe_excerpt(str(hit.get("chunk_text") or ""), 700),
        metadata={
            "document_id": document_id,
            "chunk_position": hit.get("chunk_position"),
            "query_kind": query_kind,
        },
    )


def _build_online_source(result: Any, *, query_kind: str) -> EvidenceSource:
    source_id = _stable_source_id("OL", str(result.source), str(result.title), str(result.url))
    return EvidenceSource(
        source_id=source_id,
        source_type="online-legal-research",
        title=str(result.title),
        citation=str(result.source),
        court="",
        date="",
        section="",
        page="",
        paragraph="",
        url=str(result.url),
        extracted_text=_safe_excerpt(str(getattr(result, "snippet", "") or ""), 600),
        metadata={"query_kind": query_kind},
    )


def _collect_legal_sources(plan: ResearchPlan) -> list[EvidenceSource]:
    sources: list[EvidenceSource] = []
    for query_kind, query in _plan_to_query_list(plan):
        rag_result = retrieve_legal_rag_result(query)
        for authority in (*rag_result.statute_matches, *rag_result.case_matches):
            sources.append(_build_legal_source(authority, query_kind=query_kind))
    return sources


def _collect_document_sources(user_id: str, matter_id: str, plan: ResearchPlan, query: str) -> list[EvidenceSource]:
    documents = {doc["document_id"]: doc for doc in db_client.list_matter_documents(user_id, matter_id)}
    search_queries = [query, *plan.issue_queries[:2], *plan.section_queries[:2]]
    sources: list[EvidenceSource] = []
    seen: set[str] = set()
    query_kinds = ["issue", "issue", "section", "judgment", "judgment"]
    for index, search_query in enumerate(search_queries):
        query_kind = query_kinds[index] if index < len(query_kinds) else "issue"
        for hit in search_documents(user_id, matter_id, search_query, limit=4):
            document = documents.get(str(hit.get("document_id") or ""))
            if not document:
                continue
            source = _build_document_source(document, hit, query_kind=query_kind)
            if source.source_id in seen:
                continue
            seen.add(source.source_id)
            sources.append(source)
    return sources


def _collect_online_sources(plan: ResearchPlan, query: str) -> list[EvidenceSource]:
    if not _env_flag("ONLINE_LEGAL_RESEARCH_ENABLED", False):
        return []

    sources: list[EvidenceSource] = []
    seen: set[str] = set()
    search_queries = [query, *plan.judgment_queries[:2], *plan.contrary_queries[:2]]
    query_kinds = ["issue", "judgment", "contrary", "contrary"]
    for index, search_query in enumerate(search_queries):
        query_kind = query_kinds[index] if index < len(query_kinds) else "contrary"
        for result in search_indiakanoon(search_query):
            source = _build_online_source(result, query_kind=query_kind)
            if source.source_id in seen:
                continue
            seen.add(source.source_id)
            sources.append(source)
    return sources


def _build_evidence_pack(user_id: str, matter_id: str, query: str, plan: ResearchPlan) -> list[EvidenceSource]:
    sources = _collect_legal_sources(plan)
    sources.extend(_collect_document_sources(user_id, matter_id, plan, query))
    sources.extend(_collect_online_sources(plan, query))
    return _dedupe_sources(sources)


def _render_sources_for_prompt(sources: list[EvidenceSource]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "title": source.title,
            "citation": source.citation,
            "court": source.court,
            "date": source.date,
            "section": source.section,
            "page": source.page,
            "paragraph": source.paragraph,
            "url": source.url,
            "extracted_text": source.extracted_text,
        }
        for source in sources
    ]


def _build_research_prompt(
    *,
    matter_context: dict[str, Any],
    plan: ResearchPlan,
    sources: list[EvidenceSource],
    query: str,
) -> tuple[str, str]:
    prompt_payload = {
        "matter_context": {
            key: matter_context.get(key)
            for key in ("matter_id", "title", "description", "case_number", "court", "stage", "status")
        },
        "research_plan": {
            "issue_summary": plan.issue_summary,
            "issue_queries": plan.issue_queries,
            "statute_queries": plan.statute_queries,
            "section_queries": plan.section_queries,
            "judgment_queries": plan.judgment_queries,
            "contrary_queries": plan.contrary_queries,
            "domain_labels": plan.domain_labels,
            "legal_terms": plan.legal_terms,
        },
        "evidence_pack": _render_sources_for_prompt(sources),
        "user_query": query,
    }

    return _research_system_prompt(), json.dumps(prompt_payload, ensure_ascii=False, indent=2)


def _research_system_prompt() -> str:
    return (
        "You are a legal research assistant for Indian matters.\n"
        "Return STRICT JSON only. Do not wrap it in markdown fences.\n"
        "Every material claim must include at least one source_id from the supplied evidence pack.\n"
        "If the evidence is insufficient, lower confidence and explain the gap in review_notes.\n"
        "Use the same response object to provide claims, source mappings, and confidence.\n"
        "Required JSON keys:\n"
        "{\n"
        '  "memo_title": string,\n'
        '  "memo_summary": string,\n'
        '  "claims": [\n'
        '    {"claim_id": "C1", "text": "...", "source_ids": ["S1"], "source_locations": ["section:138"], "material": true, "confidence": 0.0, "claim_type": "statute|judgment|analysis"}\n'
        "  ],\n"
        '  "source_mappings": [\n'
        '    {"source_id": "S1", "claim_ids": ["C1"], "support": "..."}\n'
        "  ],\n"
        '  "confidence": 0.0,\n'
        '  "review_notes": string\n'
        "}\n"
        "Do not invent source IDs. Do not include claims that cannot be tied to the evidence pack.\n"
        "Prefer concise claims, one issue per claim, and cite contrary authority when useful.\n"
    )


@dataclass(frozen=True)
class ResearchRunResult:
    query: str
    plan: ResearchPlan
    evidence_sources: list[EvidenceSource]
    draft: ResearchDraft
    verification: VerificationResult
    output_text: str
    saved_research: dict[str, Any] | None = None
    tokens_used: int = 0


def run_research(
    *,
    user_id: str,
    matter_id: str,
    query: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> ResearchRunResult:
    matter_context = matter_context_service.build_matter_context(
        user_id=user_id,
        matter_id=matter_id,
        conversation_history=conversation_history or [],
        max_tokens=2500,
    ).model_dump()
    plan = build_research_plan(query, matter_context)
    evidence_sources = _build_evidence_pack(user_id, matter_id, query, plan)

    if not evidence_sources:
        draft = ResearchDraft(
            memo_title="Verified Research Memo",
            memo_summary="No sufficient evidence sources were found for this research request.",
            confidence=0.0,
            claims=[],
            source_mappings=[],
            review_notes="No evidence pack could be assembled.",
            raw_text="",
        )
        verification = verify_research_draft(draft, [])
        return ResearchRunResult(
            query=query,
            plan=plan,
            evidence_sources=[],
            draft=draft,
            verification=verification,
            output_text=verification.memo_text,
        )

    system_prompt, prompt = _build_research_prompt(
        matter_context=matter_context,
        plan=plan,
        sources=evidence_sources,
        query=query,
    )
    raw_response, tokens_used = generate_notice_response(
        prompt,
        system_prompt=system_prompt,
        apply_guardrails=False,
    )
    draft = parse_research_draft(raw_response)
    verification = verify_research_draft(draft, evidence_sources)

    saved_research: dict[str, Any] | None = None
    if verification.verified:
        saved_research = db_client.create_matter_research(
            user_id=user_id,
            matter_id=matter_id,
            title=verification.memo_title,
            query=query,
            content=verification.memo_text,
            evidence=[source.to_dict() for source in verification.sources],
            verification_status="verified",
        )

    output_text = verification.memo_text
    if not verification.verified:
        output_text = f"{output_text}\n\nThis research memo was not saved because verification failed."

    return ResearchRunResult(
        query=query,
        plan=plan,
        evidence_sources=evidence_sources,
        draft=draft,
        verification=verification,
        output_text=output_text,
        saved_research=saved_research,
        tokens_used=tokens_used,
    )
