"""
Grounding helpers for stabilizing and sanitizing chat answers.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .legal_rag_service import LegalRagResult, RetrievedAuthority


_SECTION_CAPTURE_PATTERN = re.compile(r"\b(?:section|sec\.?|s\.)\s*(\d+[a-z]?(?:\(\d+\))?)\b", re.I)
_SECTION_TEXT_PATTERN = re.compile(r"\b(?:(?P<act>bns|bnss|bsa|ipc|crpc|cpc)\s+)?(?P<label>section|sec\.?|s\.)\s*(?P<number>\d+[a-z]?(?:\(\d+\))?)\b", re.I)
_CASE_CITATION_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9.&'() -]{1,80}\s+v\.?\s+[A-Z][A-Za-z0-9.&'() -]{1,80})\b")
_UNSUPPORTED_SECTION_PLACEHOLDER = "the exact current statutory provision should be verified from the statute text"


@dataclass(frozen=True)
class GroundingPolicy:
    allowed_section_numbers: frozenset[str]
    allowed_case_titles: frozenset[str]
    weak_grounding: bool


def _normalize_section_number(value: str) -> str:
    return (value or "").strip().lower()


def _normalize_case_title(value: str) -> str:
    compact = re.sub(r"\s+", " ", (value or "").strip())
    compact = re.sub(r"\bv\.?\b", "v.", compact, flags=re.I)
    return compact.lower()


def _extract_user_section_numbers(query: str) -> set[str]:
    return {
        _normalize_section_number(match.group(1))
        for match in _SECTION_CAPTURE_PATTERN.finditer(query or "")
    }


def build_grounding_policy(query: str, rag_result: LegalRagResult) -> GroundingPolicy:
    allowed_sections = _extract_user_section_numbers(query)
    for item in rag_result.statute_matches:
        allowed_sections.update(_extract_user_section_numbers(item.reference))
        allowed_sections.update(_extract_user_section_numbers(item.summary))

    allowed_case_titles = {
        _normalize_case_title(item.title)
        for item in rag_result.case_matches
        if item.title.strip()
    }
    weak_grounding = not rag_result.statute_matches and not rag_result.case_matches
    return GroundingPolicy(
        allowed_section_numbers=frozenset(filter(None, allowed_sections)),
        allowed_case_titles=frozenset(filter(None, allowed_case_titles)),
        weak_grounding=weak_grounding,
    )


def _neutralize_unsupported_sections(text: str, policy: GroundingPolicy) -> tuple[str, bool]:
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        section_number = _normalize_section_number(match.group("number"))
        if section_number in policy.allowed_section_numbers:
            return match.group(0)

        changed = True
        return _UNSUPPORTED_SECTION_PLACEHOLDER

    return _SECTION_TEXT_PATTERN.sub(replace, text), changed


def _neutralize_unsupported_case_citations(text: str, policy: GroundingPolicy) -> tuple[str, bool]:
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        case_title = _normalize_case_title(match.group(1))
        if case_title in policy.allowed_case_titles:
            return match.group(1)

        changed = True
        return "a reported decision that should be verified from authoritative sources"

    return _CASE_CITATION_PATTERN.sub(replace, text), changed


def _append_grounding_note(text: str, *, cite_warning: bool, weak_grounding: bool) -> str:
    notes: list[str] = []
    normalized = text.lower()

    if cite_warning and "exact section should be verified" not in normalized:
        notes.append(
            "Verification Note: Exact section numbers or case citations not supported by the retrieved authorities have been generalized and should be verified from the relevant statute or authoritative source."
        )
    if weak_grounding and "source support is limited" not in normalized:
        notes.append(
            "Verification Note: Source support is limited for this query, so the answer stays at a general legal-guidance level and avoids unsupported statutory details."
        )

    if not notes:
        return text.strip()

    return f"{text.rstrip()}\n\n" + "\n".join(notes)


def _cleanup_placeholder_phrases(text: str) -> str:
    cleaned = text
    cleaned = re.sub(
        re.escape("the relevant section of the applicable statute"),
        _UNSUPPORTED_SECTION_PLACEHOLDER,
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\(\s*" + re.escape(_UNSUPPORTED_SECTION_PLACEHOLDER) + r"\s*\)",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        re.escape(_UNSUPPORTED_SECTION_PLACEHOLDER) + r"\s*\(\d+(?:\([a-z0-9]+\))?\)",
        _UNSUPPORTED_SECTION_PLACEHOLDER,
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    return cleaned.strip()


def _restore_response_formatting(text: str) -> str:
    restored = text.replace("\r\n", "\n")
    restored = re.sub(r"(?<!\n)(#{2,6}\s*)", r"\n\n\1", restored)
    restored = re.sub(r"(#{2,6}\s*[^\n#]+?)(?=(?:#{2,6}|\d+\.|[A-Z][a-z]+:|$))", r"\1\n", restored)
    restored = re.sub(r"---\s*([A-Z][A-Za-z /&()-]+?)(?=(?:\d+\.|\-|:|$))", r"\n\n\1", restored)
    restored = re.sub(r"([A-Za-z])---\s*", r"\1\n\n", restored)
    heading_patterns = (
        "Opening",
        "Classification:",
        "Short Classification",
        "Intake Extraction:",
        "Known Facts",
        "Missing Facts",
        "Key Issues:",
        "Relevant Law",
        "Relevant Laws:",
        "Evidence Matrix",
        "Remedies and Forum:",
        "Risk:",
        "Risk Assessment",
        "Next Step:",
        "Immediate Action:",
        "Legal Strategy:",
        "Long-Term:",
        "Disclaimer:",
        "Follow-up",
        "Source Check:",
        "Verification Note:",
    )

    for pattern in heading_patterns:
        escaped = re.escape(pattern)
        restored = re.sub(rf"(?<!\n){escaped}", f"\n\n{pattern}", restored)

    restored = re.sub(r"(?:^|\n)(Opening)\s+", r"\n\n\1\n", restored)
    restored = re.sub(r"(?:^|\n)([A-Z][A-Za-z /&()-]{3,40})(?=-\s)", r"\n\n\1", restored)
    restored = re.sub(r"(?<!\n)(\d+\.\s+)", r"\n\1", restored)
    restored = re.sub(r"([A-Za-z]):-\s*", r"\1:\n- ", restored)
    restored = re.sub(r"(?<!\n)([A-Z][A-Za-z /&()-]{3,40})-\s+", r"\n\n\1\n- ", restored)
    restored = re.sub(r"(?<!\n)(\d+\.\s+[A-Z][^\n:]{0,80}:)", r"\n\n\1", restored)
    restored = re.sub(r"(?<!\n)([A-Z][A-Za-z /-]{2,40}:)\s*- ", r"\n\n\1\n- ", restored)
    restored = re.sub(r"\s+- ", r"\n- ", restored)
    restored = re.sub(r"(?<!\n)(\|\s*-{3,}.*?\|)", r"\n\1", restored)
    restored = re.sub(r"(?<!\n)(\|\s*[^|\n]+?\|\s*[^|\n]+?\|(?:\s*[^|\n]*\|)?)", r"\n\1", restored)
    restored = re.sub(r"\n([A-Z][A-Za-z /&()-]{3,40})\n- ([^\n]+)", r"\n\n\1:\n- \2", restored)
    restored = re.sub(r"([.:])\s*(\d+\.\s+)", r"\1\n\2", restored)
    restored = re.sub(r"Intake\s*\n+\s*Extraction:", "Intake Extraction:", restored)
    restored = re.sub(r"Known\s*\n+\s*Facts:", "Known Facts:", restored)
    restored = re.sub(r"Missing\s*\n+\s*Facts", "Missing Facts", restored)
    restored = re.sub(r"Relevant\s*\n+\s*Law", "Relevant Law", restored)
    restored = re.sub(r"Risk\s*\n+\s*Assessment", "Risk Assessment", restored)
    restored = re.sub(r"Next\s*\n+\s*Step:", "Next Step:", restored)
    restored = re.sub(r"(#{2,6})\s*\n+\s*(\d+\.\s*[^\n]+)", r"\1 \2", restored)
    restored = re.sub(r"(#{2,6})\s*\n+\s*([A-Z][^\n]+)", r"\1 \2", restored)
    restored = re.sub(r"#\s*\n+\s*###\s*(\d+\.\s*)", r"#### \1", restored)
    restored = re.sub(r"(#{2,6}\s*\d+\.)\s*\n+\s*([A-Z][^\n]+)", r"\1 \2", restored)
    restored = re.sub(r"(?<!\n)\n(#{2,6}\s*\d+\.\s*[^\n]+)", r"\n\n\1", restored)
    restored = re.sub(r"\|\s*(-{3,})\s*\n\|\s*(-{3,}\s*\|)", r"|\1|\2", restored)
    restored = re.sub(r"\|\s*\|\s*([A-Za-z0-9][^|\n]*\|)", r"| \1", restored)
    restored = re.sub(r"(\|[-| ]+[-])\s*$", r"\1|", restored, flags=re.M)
    restored = restored.replace("Remedies and \n\nForum:", "Remedies and Forum:")
    restored = re.sub(r"\n{2,}(?=\|)", "\n", restored)
    restored = re.sub(r"\n{3,}", "\n\n", restored)
    return restored.strip()


def _restore_markdown_emphasis(text: str) -> str:
    restored = text.replace("\r\n", "\n")
    restored = re.sub(r"\*\*\s*(\d+)\.\s*\n+\s*([^\n*]+)\*\*", r"**\1. \2**", restored)
    restored = re.sub(r"\*\*\s*\n+\s*(\d+)\.\s*\n+\s*([^\n*]+)\*\*", r"**\1. \2**", restored)
    restored = re.sub(r"\*\*\s*\n\s*([^\n*]+)\*\*", r"**\1**", restored)
    restored = re.sub(r"\n\*\*\s*\n", "\n", restored)
    restored = re.sub(r"^\*\*\s*$", "", restored, flags=re.M)
    restored = re.sub(r"\*\*\s{2,}", "** ", restored)
    restored = re.sub(r"\s{2,}\*\*", " **", restored)
    restored = re.sub(r"\n{3,}", "\n\n", restored)
    return restored.strip()


def sanitize_grounded_response(
    response_text: str,
    *,
    current_query: str,
    rag_result: LegalRagResult,
) -> str:
    if not response_text.strip():
        return response_text

    policy = build_grounding_policy(current_query, rag_result)
    sanitized_text, unsupported_sections_found = _neutralize_unsupported_sections(response_text, policy)
    sanitized_text, unsupported_cases_found = _neutralize_unsupported_case_citations(sanitized_text, policy)
    sanitized_text = _cleanup_placeholder_phrases(sanitized_text)
    sanitized_text = _restore_markdown_emphasis(sanitized_text)
    sanitized_text = _restore_response_formatting(sanitized_text)
    sanitized_text = _restore_markdown_emphasis(sanitized_text)

    return _append_grounding_note(
        sanitized_text,
        cite_warning=unsupported_sections_found or unsupported_cases_found,
        weak_grounding=policy.weak_grounding,
    )
