"""
AI-backed document generation for Indian legal drafting workflows.
"""

from __future__ import annotations

from ..services.bedrock_llm_service import generate_response


_FALLBACK_DOCUMENT_PROMPT = (
    "You are an Indian legal drafting assistant. Draft only the requested legal document in plain text. "
    "Do not use markdown, bold markers, emoji, checklists, drafting notes, or explanatory commentary. "
    "Do not invent facts, dates, statutory provisions, case numbers, or annexures. "
    "Use restrained placeholders in square brackets where facts are missing."
)


def _normalize_prompt(skill_prompt: str) -> str:
    cleaned = (skill_prompt or "").strip()
    return cleaned or _FALLBACK_DOCUMENT_PROMPT


def build_document_generation_prompt(
    *,
    document_type: str,
    document_type_label: str,
    party_details: str = "",
    recipient_details: str = "",
    case_details: str,
    relevant_info: str = "",
    additional_info: str = "",
    structured_fields: dict[str, str] | None = None,
    structured_sections: list[dict[str, object]] | None = None,
    skill_name: str = "",
    skill_prompt: str = "",
) -> str:
    effective_skill_prompt = _normalize_prompt(skill_prompt)
    structured_sections = structured_sections or []

    structured_text = "\n\n".join(
        (
            f"{str(section.get('title') or 'Section')}:\n"
            + "\n".join(
                f"- {str(item.get('label') or item.get('key') or 'Field')}: {str(item.get('value') or '').strip()}"
                for item in list(section.get('items') or [])
                if str(item.get('value') or '').strip()
            )
        )
        for section in structured_sections
        if any(str(item.get('value') or '').strip() for item in list(section.get('items') or []))
    )

    return (
        f"{effective_skill_prompt}\n\n"
        "Generate the requested Indian legal document using only the inputs below. "
        "Return only the final document text.\n\n"
        f"Selected document type key:\n{document_type.strip() or '[Not provided]'}\n\n"
        f"Selected document type label:\n{document_type_label.strip() or '[Not provided]'}\n\n"
        f"Selected skill name:\n{skill_name.strip() or '[Not provided]'}\n\n"
        f"Party / client details:\n{party_details.strip() or '[Party details not provided]'}\n\n"
        f"Other party / recipient details:\n{recipient_details.strip() or '[Recipient details not provided]'}\n\n"
        f"Core case details:\n{case_details.strip() or '[Case details not provided]'}\n\n"
        f"Other relevant information:\n{relevant_info.strip() or '[No additional information provided]'}\n\n"
        f"Additional information:\n{additional_info.strip() or '[No additional information provided]'}\n\n"
        f"Structured document fields:\n{structured_text or '[No structured sections provided]'}"
    )


def generate_document(
    *,
    document_type: str,
    document_type_label: str,
    party_details: str = "",
    recipient_details: str = "",
    case_details: str,
    relevant_info: str = "",
    additional_info: str = "",
    structured_fields: dict[str, str] | None = None,
    structured_sections: list[dict[str, object]] | None = None,
    skill_name: str = "",
    skill_prompt: str = "",
) -> str:
    prompt = build_document_generation_prompt(
        document_type=document_type,
        document_type_label=document_type_label,
        party_details=party_details,
        recipient_details=recipient_details,
        case_details=case_details,
        relevant_info=relevant_info,
        additional_info=additional_info,
        structured_fields=structured_fields,
        structured_sections=structured_sections,
        skill_name=skill_name,
        skill_prompt=skill_prompt,
    )
    return generate_response(prompt)
