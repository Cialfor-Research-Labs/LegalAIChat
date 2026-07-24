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
_ACT_CITATION_PATTERN = re.compile(
    r"\b(?:bns|bnss|bsa|ipc|crpc|cpc|mva|motor vehicles act|information technology act|it act|consumer protection act|specific relief act|contract act|constitution of india|articles? of the constitution)\b",
    re.I,
)
_UNSUPPORTED_SECTION_PLACEHOLDER = "the relevant provision"
_UNSUPPORTED_ACT_PLACEHOLDER = "the relevant statute"
_FINAL_VERIFICATION_NOTE = (
    "Note: This summary is based on the available legal corpus. "
    "Please refer to the official statute for authoritative legal interpretation."
)


@dataclass(frozen=True)
class GroundingPolicy:
    allowed_section_numbers: frozenset[str]
    allowed_case_titles: frozenset[str]
    allowed_act_names: frozenset[str]
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
    allowed_act_names: set[str] = set()
    for item in rag_result.statute_matches:
        allowed_sections.update(_extract_user_section_numbers(item.reference))
        allowed_sections.update(_extract_user_section_numbers(item.summary))
        allowed_act_names.add(_normalize_case_title(item.title))
        allowed_act_names.add(_normalize_case_title(item.reference))

    allowed_case_titles = {
        _normalize_case_title(item.title)
        for item in rag_result.case_matches
        if item.title.strip()
    }
    weak_grounding = not rag_result.statute_matches and not rag_result.case_matches
    return GroundingPolicy(
        allowed_section_numbers=frozenset(filter(None, allowed_sections)),
        allowed_case_titles=frozenset(filter(None, allowed_case_titles)),
        allowed_act_names=frozenset(filter(None, allowed_act_names)),
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


def _neutralize_unsupported_act_citations(text: str, policy: GroundingPolicy) -> tuple[str, bool]:
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        act_text = _normalize_case_title(match.group(0))
        if any(allowed in act_text for allowed in policy.allowed_act_names if allowed):
            return match.group(0)

        changed = True
        return _UNSUPPORTED_ACT_PLACEHOLDER

    return _ACT_CITATION_PATTERN.sub(replace, text), changed


def _append_grounding_note(text: str, *, cite_warning: bool, weak_grounding: bool) -> str:
    if not (cite_warning or weak_grounding):
        return text.strip()
    normalized = text.lower()
    if _FINAL_VERIFICATION_NOTE.lower() in normalized:
        return text.strip()
    return f"{text.rstrip()}\n\n{_FINAL_VERIFICATION_NOTE}"


def _cleanup_placeholder_phrases(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"(?im)^\s*verification note:\s*.*(?:\n|$)", "", cleaned)
    cleaned = re.sub(
        re.escape("the exact current statutory provision should be verified from the statute text"),
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        re.escape("the exact applicable statute should be verified from the retrieved documents"),
        "",
        cleaned,
        flags=re.I,
    )
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
    cleaned = re.sub(
        re.escape("the applicable statute"),
        _UNSUPPORTED_ACT_PLACEHOLDER,
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
    sanitized_text, unsupported_acts_found = _neutralize_unsupported_act_citations(sanitized_text, policy)
    sanitized_text = _cleanup_placeholder_phrases(sanitized_text)
    sanitized_text = _restore_markdown_emphasis(sanitized_text)
    sanitized_text = _restore_response_formatting(sanitized_text)
    sanitized_text = _restore_markdown_emphasis(sanitized_text)
    sanitized_text = re.sub(r"\n{3,}", "\n\n", sanitized_text).strip()

    return _append_grounding_note(
        sanitized_text,
        cite_warning=unsupported_sections_found or unsupported_cases_found or unsupported_acts_found,
        weak_grounding=policy.weak_grounding,
    )
