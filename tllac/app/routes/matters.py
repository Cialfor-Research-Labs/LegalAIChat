from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..db.db_client import db_client
from ..services.auth_service import get_current_user

router = APIRouter(prefix="/v1/matters", tags=["matters"])


class MatterCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=10000)
    case_number: str | None = Field(default=None, max_length=200)
    court: str | None = Field(default=None, max_length=300)
    jurisdiction: str | None = Field(default=None, max_length=300)
    stage: str | None = Field(default=None, max_length=200)
    status: str = Field(default="open", max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatterUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    case_number: str | None = Field(default=None, max_length=200)
    court: str | None = Field(default=None, max_length=300)
    jurisdiction: str | None = Field(default=None, max_length=300)
    stage: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] | None = None


class PartyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    party_role: str = Field(..., min_length=1, max_length=200)
    details: dict[str, Any] = Field(default_factory=dict)


class PartyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    party_role: str | None = Field(default=None, min_length=1, max_length=200)
    details: dict[str, Any] | None = None


class HearingCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    hearing_at: str | None = None
    court: str | None = Field(default=None, max_length=300)
    status: str = Field(default="scheduled", max_length=80)
    notes: str = Field(default="", max_length=12000)
    details: dict[str, Any] = Field(default_factory=dict)


class HearingUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    hearing_at: str | None = None
    court: str | None = Field(default=None, max_length=300)
    status: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=12000)
    details: dict[str, Any] | None = None


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=12000)
    due_at: str | None = None
    status: str = Field(default="open", max_length=80)
    priority: str = Field(default="normal", max_length=80)
    details: dict[str, Any] = Field(default_factory=dict)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=12000)
    due_at: str | None = None
    status: str | None = Field(default=None, max_length=80)
    priority: str | None = Field(default=None, max_length=80)
    details: dict[str, Any] | None = None


class NoteCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=30000)
    title: str = Field(default="", max_length=300)
    is_private: bool = False


class NoteUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=30000)
    title: str | None = Field(default=None, max_length=300)
    is_private: bool | None = None


class TimelineEventCreateRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=12000)
    event_at: str | None = None
    source_type: str | None = Field(default=None, max_length=200)
    source_id: str | None = Field(default=None, max_length=200)
    details: dict[str, Any] = Field(default_factory=dict)


class TimelineEventUpdateRequest(BaseModel):
    event_type: str | None = Field(default=None, min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=12000)
    event_at: str | None = None
    source_type: str | None = Field(default=None, max_length=200)
    source_id: str | None = Field(default=None, max_length=200)
    details: dict[str, Any] | None = None


class MatterListResponse(BaseModel):
    matters: list[dict[str, Any]]


class MatterOverviewResponse(BaseModel):
    matter_details: dict[str, Any]
    parties: list[dict[str, Any]]
    counsel: list[dict[str, Any]]
    hearings: list[dict[str, Any]]
    open_tasks: list[dict[str, Any]]
    notes: list[dict[str, Any]]
    timeline_events: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    research: list[dict[str, Any]]
    drafts: list[dict[str, Any]]

_RESOURCE_SPECS: dict[str, dict[str, Any]] = {
    "parties": {
        "kind": "party",
        "label": "party",
        "create_model": PartyCreateRequest,
        "update_model": PartyUpdateRequest,
    },
    "hearings": {
        "kind": "hearing",
        "label": "hearing",
        "create_model": HearingCreateRequest,
        "update_model": HearingUpdateRequest,
    },
    "tasks": {
        "kind": "task",
        "label": "task",
        "create_model": TaskCreateRequest,
        "update_model": TaskUpdateRequest,
    },
    "notes": {
        "kind": "note",
        "label": "note",
        "create_model": NoteCreateRequest,
        "update_model": NoteUpdateRequest,
    },
    "timeline-events": {
        "kind": "event",
        "label": "timeline event",
        "create_model": TimelineEventCreateRequest,
        "update_model": TimelineEventUpdateRequest,
    },
}


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


def _raise_value_error(exc: ValueError, *, resource: str = "matter") -> None:
    message = str(exc)
    lowered = message.lower()
    if "not found" in lowered or "does not belong" in lowered:
        raise _http_error(status.HTTP_404_NOT_FOUND, f"{resource}_not_found", message) from exc
    if "unsupported recent window" in lowered or "required" in lowered or "invalid" in lowered:
        raise _http_error(status.HTTP_400_BAD_REQUEST, f"{resource}_validation_error", message) from exc
    raise _http_error(status.HTTP_400_BAD_REQUEST, f"{resource}_error", message) from exc


def _require_text(payload: dict[str, Any], field: str, *, resource: str) -> str:
    value = str(payload.get(field, "")).strip()
    if not value:
        raise ValueError(f"{resource.title()} {field.replace('_', ' ')} is required.")
    return value


def _optional_text(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text_or_default(payload: dict[str, Any], field: str, default: str) -> str:
    value = payload.get(field, default)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _optional_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field.replace('_', ' ').title()} must be an object.")


def _filter_archive_state(rows: list[dict[str, Any]], archive_state: str) -> list[dict[str, Any]]:
    state = archive_state.strip().lower()
    if state == "active":
        return [row for row in rows if not row.get("is_archived")]
    if state == "archived":
        return [row for row in rows if row.get("is_archived")]
    if state == "all":
        return rows
    raise ValueError("Archive state must be one of active, archived, or all.")


def _matter_list(
    user_id: str,
    *,
    archive_state: str = "active",
    recent_window: str | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(archive_state, str):
        archive_state = getattr(archive_state, "default", "active") or "active"
    if recent_window is not None and not isinstance(recent_window, str):
        recent_window = getattr(recent_window, "default", None)
    state = archive_state.strip().lower()
    include_archived = state in {"archived", "all"}
    rows = db_client.list_matters(
        user_id,
        include_archived=include_archived,
        recent_window=recent_window,
    )
    return _filter_archive_state(rows, state)


@router.post("", response_model=dict[str, Any])
async def create_matter(
    payload: MatterCreateRequest,
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        matter = db_client.create_matter(
            user_id=user_id,
            title=payload.title.strip(),
            description=payload.description.strip(),
            case_number=payload.case_number.strip() if payload.case_number else None,
            court=payload.court.strip() if payload.court else None,
            jurisdiction=payload.jurisdiction.strip() if payload.jurisdiction else None,
            stage=payload.stage.strip() if payload.stage else None,
            status=payload.status.strip() or "open",
            metadata=payload.metadata,
        )
        return matter
    except ValueError as exc:
        _raise_value_error(exc)


@router.get("", response_model=MatterListResponse)
async def list_matters(
    archive_state: str = Query(default="active", description="Filter matters by archive state: active, archived, or all."),
    recent_window: str | None = Query(default=None, description="Optional recent window: 30d, 6m, or 1y."),
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        return MatterListResponse(matters=_matter_list(user_id, archive_state=archive_state, recent_window=recent_window))
    except ValueError as exc:
        _raise_value_error(exc)


@router.get("/recent", response_model=MatterListResponse)
async def list_recent_matters(
    window: str = Query(default="30d", description="Recent window: 30d, 6m, or 1y."),
    archive_state: str = Query(default="active", description="Filter matters by archive state: active, archived, or all."),
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        return MatterListResponse(matters=_matter_list(user_id, archive_state=archive_state, recent_window=window))
    except ValueError as exc:
        _raise_value_error(exc)


@router.get("/{matter_id}", response_model=dict[str, Any])
async def get_matter(
    matter_id: str,
    include_archived: bool = Query(default=False),
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    is_inc_arch = include_archived if isinstance(include_archived, bool) else bool(getattr(include_archived, "default", False))
    try:
        return db_client.get_matter(user_id, matter_id, include_archived=is_inc_arch)
    except ValueError as exc:
        _raise_value_error(exc)


@router.patch("/{matter_id}", response_model=dict[str, Any])
async def update_matter(
    matter_id: str,
    payload: MatterUpdateRequest,
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        changes = {
            key: value
            for key, value in {
                "title": payload.title.strip() if payload.title is not None else None,
                "description": payload.description.strip() if payload.description is not None else None,
                "case_number": payload.case_number.strip() if payload.case_number else None,
                "court": payload.court.strip() if payload.court else None,
                "jurisdiction": payload.jurisdiction.strip() if payload.jurisdiction else None,
                "stage": payload.stage.strip() if payload.stage else None,
                "status": payload.status.strip() if payload.status is not None else None,
                "metadata": payload.metadata,
            }.items()
            if value is not None
        }
        return db_client.update_matter(user_id=user_id, matter_id=matter_id, **changes)
    except ValueError as exc:
        _raise_value_error(exc)


@router.post("/{matter_id}/archive", response_model=dict[str, Any])
async def archive_matter(
    matter_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        return db_client.archive_matter(user_id=user_id, matter_id=matter_id)
    except ValueError as exc:
        _raise_value_error(exc)


@router.get("/{matter_id}/overview", response_model=MatterOverviewResponse)
async def get_matter_overview(
    matter_id: str,
    include_archived: bool = Query(default=False),
    current_user: dict[str, str] = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        return db_client.get_matter_overview(
            user_id,
            matter_id,
            include_archived=include_archived,
        )
    except ValueError as exc:
        _raise_value_error(exc)


def _register_related_routes(segment: str, spec: dict[str, Any]) -> None:
    kind = spec["kind"]
    label = spec["label"]
    create_model = spec["create_model"]
    update_model = spec["update_model"]

    async def create_related(
        matter_id: str,
        payload: dict[str, Any] | None = Body(default=None),
        current_user: dict[str, str] = Depends(get_current_user),
    ):
        user_id = current_user["user_id"]
        payload = payload or {}
        try:
            validated = create_model.model_validate(payload)
            if kind == "party":
                return db_client.create_matter_party(
                    user_id=user_id,
                    matter_id=matter_id,
                    name=validated.name.strip(),
                    party_role=validated.party_role.strip(),
                    details=validated.details,
                )
            if kind == "hearing":
                return db_client.create_matter_hearing(
                    user_id=user_id,
                    matter_id=matter_id,
                    title=validated.title.strip(),
                    hearing_at=validated.hearing_at,
                    court=validated.court.strip() if validated.court else None,
                    status=validated.status.strip() or "scheduled",
                    notes=validated.notes.strip(),
                    details=validated.details,
                )
            if kind == "task":
                return db_client.create_matter_task(
                    user_id=user_id,
                    matter_id=matter_id,
                    title=validated.title.strip(),
                    description=validated.description.strip(),
                    due_at=validated.due_at,
                    status=validated.status.strip() or "open",
                    priority=validated.priority.strip() or "normal",
                    details=validated.details,
                )
            if kind == "note":
                return db_client.create_matter_note(
                    user_id=user_id,
                    matter_id=matter_id,
                    content=validated.content.strip(),
                    title=validated.title.strip(),
                    is_private=bool(validated.is_private),
                )
            if kind == "event":
                return db_client.create_matter_event(
                    user_id=user_id,
                    matter_id=matter_id,
                    event_type=validated.event_type.strip(),
                    title=validated.title.strip(),
                    description=validated.description.strip(),
                    event_at=validated.event_at,
                    source_type=validated.source_type.strip() if validated.source_type else None,
                    source_id=validated.source_id.strip() if validated.source_id else None,
                    details=validated.details,
                )
            raise ValueError(f"Unsupported resource kind: {kind}.")
        except ValueError as exc:
            _raise_value_error(exc, resource=label)
        except HTTPException:
            raise
        except Exception as exc:
            raise _http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{label.replace(' ', '_')}_validation_error", str(exc)) from exc

    async def list_related(
        matter_id: str,
        include_archived: bool = Query(default=False),
        current_user: dict[str, str] = Depends(get_current_user),
    ):
        user_id = current_user["user_id"]
        try:
            if kind == "party":
                rows = db_client.list_matter_parties(user_id, matter_id)
            elif kind == "hearing":
                rows = db_client.list_matter_hearings(user_id, matter_id)
            elif kind == "task":
                rows = db_client.list_matter_tasks(user_id, matter_id)
            elif kind == "note":
                rows = db_client.list_matter_notes(user_id, matter_id)
            elif kind == "event":
                rows = db_client.list_matter_events(user_id, matter_id)
            else:
                raise ValueError(f"Unsupported resource kind: {kind}.")
            if include_archived:
                rows = db_client._v1_list_related(
                    kind=kind,
                    user_id=user_id,
                    matter_id=matter_id,
                    include_archived=True,
                )
            return {segment.replace("-", "_"): rows}
        except ValueError as exc:
            _raise_value_error(exc, resource=label)

    async def get_related(
        matter_id: str,
        record_id: str,
        include_archived: bool = Query(default=False),
        current_user: dict[str, str] = Depends(get_current_user),
    ):
        user_id = current_user["user_id"]
        try:
            return db_client.get_matter_related_record(
                kind=kind,
                user_id=user_id,
                matter_id=matter_id,
                record_id=record_id,
                include_archived=include_archived,
            )
        except ValueError as exc:
            _raise_value_error(exc, resource=label)

    async def update_related(
        matter_id: str,
        record_id: str,
        payload: dict[str, Any] | None = Body(default=None),
        current_user: dict[str, str] = Depends(get_current_user),
    ):
        user_id = current_user["user_id"]
        payload = payload or {}
        try:
            validated = update_model.model_validate(payload)
            changes: dict[str, Any] = {}
            if kind == "party":
                if validated.name is not None:
                    changes["name"] = validated.name.strip()
                if validated.party_role is not None:
                    changes["party_role"] = validated.party_role.strip()
                if validated.details is not None:
                    changes["details"] = validated.details
            elif kind == "hearing":
                if validated.title is not None:
                    changes["title"] = validated.title.strip()
                if validated.hearing_at is not None:
                    changes["hearing_at"] = validated.hearing_at
                if validated.court is not None:
                    changes["court"] = validated.court.strip() or None
                if validated.status is not None:
                    changes["status"] = validated.status.strip() or "scheduled"
                if validated.notes is not None:
                    changes["notes"] = validated.notes.strip()
                if validated.details is not None:
                    changes["details"] = validated.details
            elif kind == "task":
                if validated.title is not None:
                    changes["title"] = validated.title.strip()
                if validated.description is not None:
                    changes["description"] = validated.description.strip()
                if validated.due_at is not None:
                    changes["due_at"] = validated.due_at
                if validated.status is not None:
                    changes["status"] = validated.status.strip() or "open"
                if validated.priority is not None:
                    changes["priority"] = validated.priority.strip() or "normal"
                if validated.details is not None:
                    changes["details"] = validated.details
            elif kind == "note":
                if validated.content is not None:
                    changes["content"] = validated.content.strip()
                if validated.title is not None:
                    changes["title"] = validated.title.strip()
                if validated.is_private is not None:
                    changes["is_private"] = bool(validated.is_private)
            elif kind == "event":
                if validated.event_type is not None:
                    changes["event_type"] = validated.event_type.strip()
                if validated.title is not None:
                    changes["title"] = validated.title.strip()
                if validated.description is not None:
                    changes["description"] = validated.description.strip()
                if validated.event_at is not None:
                    changes["event_at"] = validated.event_at
                if validated.source_type is not None:
                    changes["source_type"] = validated.source_type.strip() or None
                if validated.source_id is not None:
                    changes["source_id"] = validated.source_id.strip() or None
                if validated.details is not None:
                    changes["details"] = validated.details
            if not changes:
                return db_client.get_matter_related_record(
                    kind=kind,
                    user_id=user_id,
                    matter_id=matter_id,
                    record_id=record_id,
                )
            return db_client.update_matter_related_record(
                kind=kind,
                user_id=user_id,
                matter_id=matter_id,
                record_id=record_id,
                **changes,
            )
        except ValueError as exc:
            _raise_value_error(exc, resource=label)
        except HTTPException:
            raise
        except Exception as exc:
            raise _http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{label.replace(' ', '_')}_validation_error", str(exc)) from exc

    async def archive_related(
        matter_id: str,
        record_id: str,
        current_user: dict[str, str] = Depends(get_current_user),
    ):
        user_id = current_user["user_id"]
        try:
            return db_client.archive_matter_related_record(
                kind=kind,
                user_id=user_id,
                matter_id=matter_id,
                record_id=record_id,
            )
        except ValueError as exc:
            _raise_value_error(exc, resource=label)

    router.add_api_route(
        f"/{{matter_id}}/{segment}",
        create_related,
        methods=["POST"],
        name=f"create_{segment}",
    )
    router.add_api_route(
        f"/{{matter_id}}/{segment}",
        list_related,
        methods=["GET"],
        name=f"list_{segment}",
    )
    router.add_api_route(
        f"/{{matter_id}}/{segment}/{{record_id}}",
        get_related,
        methods=["GET"],
        name=f"get_{segment}_item",
    )
    router.add_api_route(
        f"/{{matter_id}}/{segment}/{{record_id}}",
        update_related,
        methods=["PATCH"],
        name=f"update_{segment}_item",
    )
    router.add_api_route(
        f"/{{matter_id}}/{segment}/{{record_id}}/archive",
        archive_related,
        methods=["POST"],
        name=f"archive_{segment}_item",
    )


for segment, spec in _RESOURCE_SPECS.items():
    _register_related_routes(segment, spec)
