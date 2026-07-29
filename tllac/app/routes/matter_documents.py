from __future__ import annotations

from pathlib import Path
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..services.auth_service import get_current_user
from ..services.matter_document_service import (
    archive_document,
    delete_document,
    get_document_file_path,
    get_document_metadata,
    list_documents,
    process_uploaded_document,
    search_documents,
)

logger = logging.getLogger("tllac.routes.matter_documents")

router = APIRouter(prefix="/matter-documents", tags=["matter-documents"])


class MatterDocumentMetadata(BaseModel):
    document_id: str
    user_id: str
    matter_id: str
    original_filename: str
    storage_path: str
    mime_type: str
    file_extension: str
    upload_timestamp: str
    status: str
    chunk_count: int = 0


class MatterDocumentSearchRequest(BaseModel):
    matter_id: str = Field(..., min_length=1, max_length=128)
    query: str = Field(..., min_length=2, max_length=4000)
    limit: int = Field(default=10, ge=1, le=25)


class MatterDocumentSearchResult(BaseModel):
    chunk_text: str
    document_id: str
    document_name: str
    page_number: int | None = None
    paragraph_number: int | None = None
    chunk_position: int


class MatterDocumentSearchResponse(BaseModel):
    items: list[MatterDocumentSearchResult]


def _value_error_to_http_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    lowered = message.lower()
    if "not found" in lowered or "unavailable" in lowered:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@router.post("/upload", response_model=MatterDocumentMetadata)
async def upload_document(
    matter_id: str = Form(..., min_length=1, max_length=128),
    file: UploadFile = File(...),
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        document = process_uploaded_document(
            user_id=current_user["user_id"],
            matter_id=matter_id.strip(),
            uploaded_file=file,
        )
    except ValueError as exc:
        raise _value_error_to_http_error(exc) from exc
    finally:
        await file.close()
    return MatterDocumentMetadata(**document)


@router.get("", response_model=list[MatterDocumentMetadata])
async def list_matter_documents(
    matter_id: str = Query(..., min_length=1, max_length=128),
    current_user: dict[str, str] = Depends(get_current_user),
):
    return [
        MatterDocumentMetadata(**document)
        for document in list_documents(current_user["user_id"], matter_id.strip())
    ]


@router.get("/search", response_model=MatterDocumentSearchResponse)
async def search_matter_documents_get(
    matter_id: str = Query(..., min_length=1, max_length=128),
    query: str = Query(..., min_length=2, max_length=4000),
    limit: int = Query(default=10, ge=1, le=25),
    current_user: dict[str, str] = Depends(get_current_user),
):
    items = search_documents(current_user["user_id"], matter_id.strip(), query, limit=limit)
    return MatterDocumentSearchResponse(
        items=[MatterDocumentSearchResult(**item) for item in items]
    )


@router.post("/search", response_model=MatterDocumentSearchResponse)
async def search_matter_documents_post(
    request: MatterDocumentSearchRequest,
    current_user: dict[str, str] = Depends(get_current_user),
):
    items = search_documents(current_user["user_id"], request.matter_id.strip(), request.query, limit=request.limit)
    return MatterDocumentSearchResponse(
        items=[MatterDocumentSearchResult(**item) for item in items]
    )


@router.get("/{document_id}", response_model=MatterDocumentMetadata)
async def get_document_details(
    document_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        return MatterDocumentMetadata(**get_document_metadata(current_user["user_id"], document_id))
    except ValueError as exc:
        raise _value_error_to_http_error(exc) from exc


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        metadata = get_document_metadata(current_user["user_id"], document_id)
        storage_path = get_document_file_path(current_user["user_id"], document_id)
    except ValueError as exc:
        raise _value_error_to_http_error(exc) from exc

    return FileResponse(
        path=str(storage_path),
        media_type=metadata["mime_type"] or "application/octet-stream",
        filename=metadata["original_filename"],
    )


@router.get("/{document_id}/view")
async def view_document(
    document_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        metadata = get_document_metadata(current_user["user_id"], document_id)
        storage_path = get_document_file_path(current_user["user_id"], document_id)
    except ValueError as exc:
        raise _value_error_to_http_error(exc) from exc

    return FileResponse(
        path=str(storage_path),
        media_type=metadata["mime_type"] or "application/octet-stream",
        filename=metadata["original_filename"],
        content_disposition_type="inline",
    )


@router.delete("/{document_id}", response_model=MatterDocumentMetadata)
async def delete_document_endpoint(
    document_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        metadata = get_document_metadata(current_user["user_id"], document_id)
        result = delete_document(current_user["user_id"], document_id)
        storage_path = Path(metadata["storage_path"])
        if storage_path.is_file():
            storage_path.unlink()
    except ValueError as exc:
        raise _value_error_to_http_error(exc) from exc
    return MatterDocumentMetadata(**result)


@router.post("/{document_id}/archive", response_model=MatterDocumentMetadata)
async def archive_document_endpoint(
    document_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        result = archive_document(current_user["user_id"], document_id)
    except ValueError as exc:
        raise _value_error_to_http_error(exc) from exc
    return MatterDocumentMetadata(**result)
