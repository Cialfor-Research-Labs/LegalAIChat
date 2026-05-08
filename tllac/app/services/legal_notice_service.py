"""
AI-backed legal notice generation for Indian legal workflows.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..services.bedrock_llm_service import generate_response


_REPO_ROOT = Path(__file__).resolve().parents[3]
_NOTICE_PROMPT_PATH = _REPO_ROOT / "NoticeGenerator.md"
_FALLBACK_NOTICE_PROMPT = (
    "You are Legal Notice Generator AI, a senior Indian advocate's drafting assistant. "
    "Draft only a formal Indian legal notice in plain text. Do not use markdown, bold markers, "
    "emoji, symbols, checklists, tables, or drafting notes. Use clean numbered paragraphs, "
    "professional advocate language, and do not invent facts."
)


@lru_cache(maxsize=1)
def get_notice_generator_prompt() -> str:
    try:
        prompt = _NOTICE_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return _FALLBACK_NOTICE_PROMPT

    return prompt or _FALLBACK_NOTICE_PROMPT


def build_legal_notice_prompt(
    *,
    client_details: str,
    lawyer_details: str,
    case_details: str,
    recipient_details: str = "",
    relevant_info: str = "",
) -> str:
    return (
        f"{get_notice_generator_prompt()}\n\n"
        "Generate the legal notice using only the case inputs below. Return only the final notice text.\n\n"
        f"Client name and details:\n{client_details.strip() or '[Client details not provided]'}\n\n"
        f"Lawyer/advocate details:\n{lawyer_details.strip() or '[Lawyer details not provided]'}\n\n"
        f"Recipient/opposite party details:\n{recipient_details.strip() or '[Recipient details not provided]'}\n\n"
        f"Case details:\n{case_details.strip() or '[Case details not provided]'}\n\n"
        f"Other relevant information:\n{relevant_info.strip() or '[No additional information provided]'}"
    )


def generate_legal_notice(
    *,
    client_details: str,
    lawyer_details: str,
    case_details: str,
    recipient_details: str = "",
    relevant_info: str = "",
) -> str:
    prompt = build_legal_notice_prompt(
        client_details=client_details,
        lawyer_details=lawyer_details,
        recipient_details=recipient_details,
        case_details=case_details,
        relevant_info=relevant_info,
    )
    return generate_response(prompt, use_knowledge_base=False)
