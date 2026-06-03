"""
Document generator route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.auth_service import get_current_user
from ..services.document_generator_service import generate_document


router = APIRouter(prefix="/document-generator", tags=["document-generator"])


class DocumentGeneratorRequest(BaseModel):
    document_type: str = Field(..., min_length=2, max_length=120)
    document_type_label: str = Field(..., min_length=2, max_length=200)
    party_details: str = Field(default="", max_length=6000)
    recipient_details: str = Field(default="", max_length=6000)
    case_details: str = Field(..., min_length=5, max_length=16000)
    relevant_info: str = Field(default="", max_length=10000)
    skill_name: str = Field(default="", max_length=200)
    skill_prompt: str = Field(default="", max_length=60000)
    frontend_source: str = Field(default="", max_length=100)


class DocumentGeneratorResponse(BaseModel):
    document: str


@router.post("/generate", response_model=DocumentGeneratorResponse)
async def generate_document_endpoint(
    request: DocumentGeneratorRequest,
    current_user: dict[str, str] = Depends(get_current_user),
):
    _ = current_user

    document = generate_document(
        document_type=request.document_type,
        document_type_label=request.document_type_label,
        party_details=request.party_details,
        recipient_details=request.recipient_details,
        case_details=request.case_details,
        relevant_info=request.relevant_info,
        skill_name=request.skill_name,
        skill_prompt=request.skill_prompt,
    )

    if not document:
        raise HTTPException(status_code=502, detail="Document generator returned an empty response.")

    return DocumentGeneratorResponse(document=document)
