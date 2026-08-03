from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .legal_framework import classify_domains
from .legal_rag_service import analyze_legal_query


def _normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        cleaned = _normalize_query(item)
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        ordered.append(cleaned)
    return ordered


@dataclass(frozen=True)
class ResearchPlan:
    issue_summary: str
    issue_queries: list[str] = field(default_factory=list)
    statute_queries: list[str] = field(default_factory=list)
    section_queries: list[str] = field(default_factory=list)
    judgment_queries: list[str] = field(default_factory=list)
    contrary_queries: list[str] = field(default_factory=list)
    domain_labels: list[str] = field(default_factory=list)
    legal_terms: dict[str, list[str]] = field(default_factory=dict)

    def all_queries(self) -> list[str]:
        return _dedupe(
            [
                *self.issue_queries,
                *self.statute_queries,
                *self.section_queries,
                *self.judgment_queries,
                *self.contrary_queries,
            ]
        )


def _build_issue_summary(query: str, domain_labels: list[str], analysis) -> str:
    if analysis.section_numbers and analysis.act_keys:
        section_bits = ", ".join(sorted(analysis.section_numbers))
        act_bits = ", ".join(sorted(analysis.act_keys))
        base = f"Interpret the issue under {act_bits} with focus on sections {section_bits}."
    elif domain_labels:
        base = f"Likely issues: {', '.join(domain_labels)}."
    else:
        base = "Identify the core legal issue, the governing statute, and the key remedy or defense."

    if query:
        return f"{base} Query: {query}"
    return base


def build_research_plan(query: str, matter_context: dict[str, Any] | None = None) -> ResearchPlan:
    normalized_query = _normalize_query(query)
    analysis = analyze_legal_query(normalized_query)
    domains = classify_domains(normalized_query)
    domain_labels = [item.domain for item in domains[:3]]

    matter_bits: list[str] = []
    if matter_context:
        for key in ("title", "case_number", "court", "stage"):
            value = str(matter_context.get(key) or "").strip()
            if value:
                matter_bits.append(value)

    issue_queries = [normalized_query]
    issue_queries.extend(
        f"{label}: {normalized_query}"
        for label in domain_labels[:2]
    )
    if matter_bits:
        issue_queries.append(f"Matter context: {' | '.join(matter_bits)}")

    statute_queries = [normalized_query]
    if analysis.act_keys:
        statute_queries.extend(
            f"{act.replace('_', ' ')} statutory provisions"
            for act in sorted(analysis.act_keys)
        )
    else:
        statute_queries.extend(
            f"{item.domain} relevant statutes"
            for item in domains[:2]
        )

    section_queries = [normalized_query]
    for section in sorted(analysis.section_numbers):
        section_queries.append(f"Section {section} legal authority")
    if analysis.act_keys and analysis.section_numbers:
        for act in sorted(analysis.act_keys):
            for section in sorted(analysis.section_numbers):
                section_queries.append(f"{act.replace('_', ' ')} section {section}")

    judgment_queries = [normalized_query]
    judgment_queries.extend(
        f"{normalized_query} relevant judgments"
        for _ in range(1)
    )
    if section_queries:
        judgment_queries.extend(
            f"Case law on {query_fragment}"
            for query_fragment in section_queries[:2]
        )

    contrary_queries = [
        f"Contrary authority for {normalized_query}",
        f"Distinguishing judgments for {normalized_query}",
    ]
    if analysis.section_numbers:
        contrary_queries.extend(
            f"Contrary authority section {section}"
            for section in sorted(analysis.section_numbers)
        )

    legal_terms = {
        "acts": sorted(analysis.act_keys),
        "sections": sorted(analysis.section_numbers),
        "articles": sorted(analysis.article_numbers),
        "cases": sorted(analysis.case_titles),
    }

    return ResearchPlan(
        issue_summary=_build_issue_summary(normalized_query, domain_labels, analysis),
        issue_queries=_dedupe(issue_queries),
        statute_queries=_dedupe(statute_queries),
        section_queries=_dedupe(section_queries),
        judgment_queries=_dedupe(judgment_queries),
        contrary_queries=_dedupe(contrary_queries),
        domain_labels=_dedupe(domain_labels),
        legal_terms=legal_terms,
    )
