"""
Legal notice generation route.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.legal_notice_service import generate_legal_notice


router = APIRouter(prefix="/legal-notice", tags=["legal-notice"])


class LegalNoticeRequest(BaseModel):
    client_details: str = Field(default="", max_length=4000)
    lawyer_details: str = Field(default="", max_length=4000)
    recipient_details: str = Field(default="", max_length=4000)
    case_details: str = Field(..., min_length=5, max_length=12000)
    relevant_info: str = Field(default="", max_length=8000)


class LegalNoticeResponse(BaseModel):
    notice: str


@router.post("/generate", response_model=LegalNoticeResponse)
async def generate_legal_notice_endpoint(request: LegalNoticeRequest):
    notice = generate_legal_notice(
        client_details=request.client_details,
        lawyer_details=request.lawyer_details,
        recipient_details=request.recipient_details,
        case_details=request.case_details,
        relevant_info=request.relevant_info,
    )

    if not notice:
        raise HTTPException(status_code=502, detail="Legal notice generator returned an empty response.")

    return LegalNoticeResponse(notice=notice)
