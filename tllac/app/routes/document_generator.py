"""
Document generator route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..db.db_client import db_client
from ..services.auth_service import get_current_user
from ..services.document_generator_service import generate_document


router = APIRouter(prefix="/document-generator", tags=["document-generator"])


class DocumentGeneratorRequest(BaseModel):
    class StructuredItem(BaseModel):
        key: str = Field(default="", max_length=120)
        label: str = Field(default="", max_length=200)
        value: str = Field(default="", max_length=12000)

    class StructuredSection(BaseModel):
        key: str = Field(default="", max_length=120)
        title: str = Field(default="", max_length=200)
        items: list["DocumentGeneratorRequest.StructuredItem"] = Field(default_factory=list)

    document_type: str = Field(..., min_length=2, max_length=120)
    document_type_label: str = Field(..., min_length=2, max_length=200)
    party_details: str = Field(default="", max_length=6000)
    recipient_details: str = Field(default="", max_length=6000)
    case_details: str = Field(..., min_length=5, max_length=16000)
    relevant_info: str = Field(default="", max_length=10000)
    additional_info: str = Field(default="", max_length=12000)
    structured_fields: dict[str, str] = Field(default_factory=dict)
    structured_sections: list["DocumentGeneratorRequest.StructuredSection"] = Field(default_factory=list)
    skill_name: str = Field(default="", max_length=200)
    skill_prompt: str = Field(default="", max_length=60000)
    frontend_source: str = Field(default="", max_length=100)


class DocumentGeneratorResponse(BaseModel):
    document: str
    history_id: str


class DocumentHistoryDetail(BaseModel):
    artifact_id: str
    title: str
    created_at: str
    updated_at: str
    input_payload: dict
    output_text: str


@router.post("/generate", response_model=DocumentGeneratorResponse)
async def generate_document_endpoint(
    request: DocumentGeneratorRequest,
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    # Enforce daily token limit / cooldown before hitting the LLM
    db_client.check_and_enforce_limits(user_id)

    document = generate_document(
        document_type=request.document_type,
        document_type_label=request.document_type_label,
        party_details=request.party_details,
        recipient_details=request.recipient_details,
        case_details=request.case_details,
        relevant_info=request.relevant_info,
        additional_info=request.additional_info,
        structured_fields=request.structured_fields,
        structured_sections=[
            {
                "key": section.key,
                "title": section.title,
                "items": [
                    {"key": item.key, "label": item.label, "value": item.value}
                    for item in section.items
                ],
            }
            for section in request.structured_sections
        ],
        skill_name=request.skill_name,
        skill_prompt=request.skill_prompt,
    )

    if not document:
        raise HTTPException(status_code=502, detail="Document generator returned an empty response.")

    # Record token usage
    db_client.record_token_usage(user_id, request.case_details + document)

    history_id = db_client.save_generated_artifact(
        user_id=user_id,
        artifact_type="document_generator",
        title=request.document_type_label.strip() or request.document_type.strip(),
        input_payload=request.model_dump(),
        output_text=document,
    )

    return DocumentGeneratorResponse(document=document, history_id=history_id)


@router.get("/history")
async def list_document_history(
    current_user: dict[str, str] = Depends(get_current_user),
):
    return {"items": db_client.list_generated_artifacts(current_user["user_id"], "document_generator")}


@router.get("/history/{artifact_id}", response_model=DocumentHistoryDetail)
async def get_document_history(
    artifact_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        return DocumentHistoryDetail(
            **db_client.get_generated_artifact(current_user["user_id"], artifact_id, "document_generator")
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
