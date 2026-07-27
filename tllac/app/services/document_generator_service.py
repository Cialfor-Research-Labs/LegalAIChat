"""
AI-backed document generation for Indian legal drafting workflows.
"""

from __future__ import annotations

import re

from ..services.bedrock_llm_service import generate_notice_response


_FALLBACK_DOCUMENT_PROMPT = (
    "You are an Indian legal drafting assistant. Draft only the requested legal document in plain text. "
    "Do not use markdown, bold markers, emoji, checklists, drafting notes, or explanatory commentary. "
    "Do not invent facts, dates, statutory provisions, case numbers, or annexures. "
    "Use restrained placeholders in square brackets where facts are missing."
)

_TOTAL_LINE_WIDTH = 108
_LEFT_COLUMN_WIDTH = 40
_SIGNATURE_LINE = "_" * 20
_ADDRESS_LINE = "_" * 24


def _join_columns(left: str = "", right: str = "") -> str:
    if not right:
        return left.rstrip()

    safe_left = left.rstrip()
    safe_right = right.rstrip()
    min_gap = 4
    right_start = max(_LEFT_COLUMN_WIDTH + min_gap, _TOTAL_LINE_WIDTH - len(safe_right))
    gap_width = max(min_gap, right_start - len(safe_left))
    return f"{safe_left}{' ' * gap_width}{safe_right}".rstrip()


def _clean_role_text(label: str) -> str:
    compact = re.sub(r"\s+", " ", (label or "").strip())
    compact = re.sub(r"\b(full\s+name|name|address|details|description|contact|number)\b", "", compact, flags=re.I)
    compact = compact.replace("(", " ").replace(")", " ")
    compact = re.sub(r"\s+", " ", compact).strip(" /-")
    if not compact:
        return "PARTY"

    role_aliases = {
        "lessor": "LESSOR",
        "owner": "LESSOR",
        "landlord": "LESSOR",
        "lessee": "LESSEE",
        "tenant": "LESSEE",
        "occupant": "LESSEE",
        "client": "CLIENT",
        "service provider": "SERVICE PROVIDER",
        "vendor": "VENDOR",
        "consultant": "CONSULTANT",
        "contractor": "CONTRACTOR",
        "employee": "EMPLOYEE",
        "employer": "EMPLOYER",
        "plaintiff": "PLAINTIFF",
        "defendant": "DEFENDANT",
        "petitioner": "PETITIONER",
        "respondent": "RESPONDENT",
        "applicant": "APPLICANT",
        "deponent": "DEPONENT",
        "executant": "EXECUTANT",
        "opposite party": "OPPOSITE PARTY",
        "counterparty": "COUNTERPARTY",
        "company": "COMPANY",
        "subscriber": "SUBSCRIBER",
        "authorised signatory": "AUTHORISED SIGNATORY",
        "issuing authority": "ISSUING AUTHORITY",
    }

    parts = [part.strip() for part in compact.split("/") if part.strip()]
    for part in reversed(parts or [compact]):
        lowered = part.lower()
        for key, value in role_aliases.items():
            if key in lowered:
                return value

    return compact.upper()


def _extract_section_lookup(
    structured_sections: list[dict[str, object]] | None,
) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for section in structured_sections or []:
        items = {
            str(item.get("key") or ""): str(item.get("value") or "").strip()
            for item in list(section.get("items") or [])
            if str(item.get("key") or "").strip()
        }
        lookup[str(section.get("key") or "")] = items
    return lookup


def _extract_block(section: dict[str, object] | None, fallback_title: str) -> dict[str, str]:
    items = list((section or {}).get("items") or [])
    name_label = ""
    name_value = ""
    address_value = ""

    for item in items:
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        lowered = label.lower()
        if not value:
            continue
        if not name_value and any(token in lowered for token in ("name", "party", "authority", "signatory", "company")):
            name_label = label or fallback_title
            name_value = value
        if not address_value and "address" in lowered:
            address_value = value

    if not name_value and items:
        first_item = next((item for item in items if str(item.get("value") or "").strip()), None)
        if first_item is not None:
            name_label = str(first_item.get("label") or fallback_title)
            name_value = str(first_item.get("value") or "").strip()

    title = _clean_role_text(name_label or fallback_title)

    return {
        "title": title,
        "name": name_value,
        "address": address_value,
    }


def _split_witness_names(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return []
    return [part.strip() for part in re.split(r"[,\n;]+", raw_value) if part.strip()]


def build_signature_block(
    *,
    structured_sections: list[dict[str, object]] | None = None,
) -> str:
    section_map = {
        str(section.get("key") or ""): section
        for section in structured_sections or []
    }
    field_lookup = _extract_section_lookup(structured_sections)

    left_block = _extract_block(section_map.get("party-details"), "First Party")
    right_block = _extract_block(section_map.get("recipient-details"), "Second Party")

    signature_info = field_lookup.get("signatures-witnesses", {})
    execution_date = signature_info.get("date_of_execution", "")
    witness_names = _split_witness_names(
        signature_info.get("witness_names", "") or signature_info.get("witness_details", "")
    )

    left_witness_name = witness_names[0] if len(witness_names) > 0 else _SIGNATURE_LINE
    right_witness_name = witness_names[1] if len(witness_names) > 1 else _SIGNATURE_LINE

    lines = [
        "",
        "",
        _join_columns(left_block["title"], right_block["title"] or "SECOND PARTY"),
        "",
        _join_columns(
            f"Name: {left_block['name'] or _SIGNATURE_LINE}",
            f"Name: {right_block['name'] or _SIGNATURE_LINE}",
        ),
        "",
        _join_columns(
            f"Signature: {_SIGNATURE_LINE}",
            f"Signature: {_SIGNATURE_LINE}",
        ),
        "",
        _join_columns(
            f"Date: {execution_date or _SIGNATURE_LINE}",
            f"Date: {execution_date or _SIGNATURE_LINE}",
        ),
        "",
        "",
        _join_columns("WITNESS 1", "WITNESS 2"),
        "",
        _join_columns(f"Name: {left_witness_name}", f"Name: {right_witness_name}"),
        _join_columns(f"Signature: {_SIGNATURE_LINE}", f"Signature: {_SIGNATURE_LINE}"),
        _join_columns(
            f"Address: {_ADDRESS_LINE}",
            f"Address: {_ADDRESS_LINE}",
        ),
    ]

    return "\n".join(lines).rstrip()


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
        "Return only the final document text. "
        "Do not include any signature block, witness block, attestation block, or execution block at the end; "
        "that layout will be appended separately.\n\n"
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
    system_prompt = _normalize_prompt(skill_prompt)
    document_body_text, tokens_used = generate_notice_response(prompt, system_prompt, apply_guardrails=False)
    document_body = (document_body_text or "").rstrip()
    signature_block = build_signature_block(structured_sections=structured_sections)
    return f"{document_body}{signature_block}".strip(), tokens_used

