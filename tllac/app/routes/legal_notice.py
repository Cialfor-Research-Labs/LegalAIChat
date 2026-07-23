"""
Legal notice generation route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..db.db_client import db_client
from ..services.auth_service import get_current_user
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
    history_id: str


class LegalNoticeHistoryItem(BaseModel):
    artifact_id: str
    title: str
    created_at: str
    updated_at: str


class LegalNoticeHistoryDetail(BaseModel):
    artifact_id: str
    title: str
    created_at: str
    updated_at: str
    input_payload: dict
    output_text: str


@router.post("/generate", response_model=LegalNoticeResponse)
async def generate_legal_notice_endpoint(
    request: LegalNoticeRequest,
    current_user: dict[str, str] = Depends(get_current_user),
):
    notice = generate_legal_notice(
        client_details=request.client_details,
        lawyer_details=request.lawyer_details,
        recipient_details=request.recipient_details,
        case_details=request.case_details,
        relevant_info=request.relevant_info,
    )

    if not notice:
        raise HTTPException(status_code=502, detail="Legal notice generator returned an empty response.")

    history_id = db_client.save_generated_artifact(
        user_id=current_user["user_id"],
        artifact_type="legal_notice",
        title=request.case_details.strip()[:120] or "Legal Notice",
        input_payload=request.model_dump(),
        output_text=notice,
    )

    return LegalNoticeResponse(notice=notice, history_id=history_id)


@router.get("/history")
async def list_legal_notice_history(
    current_user: dict[str, str] = Depends(get_current_user),
):
    return {"items": db_client.list_generated_artifacts(current_user["user_id"], "legal_notice")}


@router.get("/history/{artifact_id}", response_model=LegalNoticeHistoryDetail)
async def get_legal_notice_history(
    artifact_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        return LegalNoticeHistoryDetail(
            **db_client.get_generated_artifact(current_user["user_id"], artifact_id, "legal_notice")
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
