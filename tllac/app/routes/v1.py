from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..db.db_client import db_client
from ..services.agent_command_service import (
    advanced_commands_enabled,
    build_brief_preview,
    build_draft_preview,
    build_next_preview,
    build_review_report,
    build_timeline_preview,
    compare_text_versions,
)
from ..services.auth_service import create_access_token, get_current_user
from ..services.bedrock_llm_service import generate_response

router = APIRouter(prefix="/v1", tags=["v1"])

_launch_tokens: dict[str, tuple[str, datetime]] = {}
_store_path = Path(__file__).resolve().parents[2] / "data" / "v1_workspace.json"
_store_lock = Lock()
_statutes_path = Path(__file__).resolve().parents[2] / "data" / "statute_sections.json"


def _load_store() -> dict[str, Any]:
    try:
        return json.loads(_store_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"matters": {}, "feedback": {}, "verified": {}, "pending_actions": {}, "idempotency": {}}


_store = _load_store()
_matters: dict[str, dict[str, dict[str, Any]]] = _store["matters"]
_feedback: dict[str, list[dict[str, Any]]] = _store["feedback"]
_verified: dict[str, set[str]] = {key: set(value) for key, value in _store.get("verified", {}).items()}
_pending_actions: dict[str, dict[str, Any]] = _store.get("pending_actions", {})
_idempotency: dict[str, str] = _store.get("idempotency", {})


def _persist() -> None:
    with _store_lock:
        _store_path.parent.mkdir(parents=True, exist_ok=True)
        _store_path.write_text(
            json.dumps(
                {
                    "matters": _matters,
                    "feedback": _feedback,
                    "verified": {key: list(value) for key, value in _verified.items()},
                    "pending_actions": _pending_actions,
                    "idempotency": _idempotency,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def _require_advanced_commands() -> None:
    if not advanced_commands_enabled():
        raise HTTPException(status_code=503, detail="Advanced agent commands are disabled until research verification is enabled.")


def _preview_key(user_id: str, matter_id: str, action: str, payload: dict[str, Any]) -> str:
    material = json.dumps({"user_id": user_id, "matter_id": matter_id, "action": action, "payload": payload}, sort_keys=True, default=str)
    return uuid4().hex if not material else uuid4().hex


def _store_preview(user_id: str, matter_id: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = uuid4().hex
    _pending_actions[token] = {
        "user_id": user_id,
        "matter_id": matter_id,
        "action": action,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _persist()
    return {"preview_token": token, **payload}


def _consume_preview(token: str, user_id: str, matter_id: str, action: str) -> dict[str, Any]:
    pending = _pending_actions.get(token)
    if not pending:
        raise HTTPException(status_code=404, detail="Preview token not found.")
    if pending.get("user_id") != user_id or pending.get("matter_id") != matter_id or pending.get("action") != action:
        raise HTTPException(status_code=403, detail="Preview token does not match this action.")
    return pending["payload"]


def _record_idempotency(key: str, result_id: str) -> None:
    _idempotency[key] = result_id
    _persist()


def _legal_sources(query: str, limit: int = 5) -> list[dict[str, Any]]:
    terms = {term.lower() for term in query.split() if len(term) > 3}
    try:
        statutes = json.loads(_statutes_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    matches = []
    for statute in statutes:
        searchable = " ".join(str(statute.get(key, "")) for key in ("act_name", "section", "title", "description", "keywords")).lower()
        if terms and any(term in searchable for term in terms):
            matches.append(statute)
        if len(matches) >= limit:
            break
    return matches


def _verified_research_source_ids(user_id: str, matter_id: str) -> set[str]:
    source_ids: set[str] = set()
    for research in db_client.list_matter_research(user_id, matter_id):
        if str(research.get("verification_status") or "").lower() != "verified":
            continue
        research_id = str(research.get("research_id") or "").strip()
        if research_id:
            source_ids.add(research_id)
        for evidence_item in research.get("evidence") or []:
            source_id = str((evidence_item or {}).get("source_id") or "").strip()
            if source_id:
                source_ids.add(source_id)
    return source_ids


def _resolve_document_location(text: str, location: str) -> str:
    try:
        kind, raw_index = location.split(":", 1)
        index = max(int(raw_index) - 1, 0)
    except (ValueError, AttributeError):
        return text[:2500]
    if kind == "paragraph":
        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        return paragraphs[index] if index < len(paragraphs) else "Location not found in extracted text."
    if kind in {"page", "chunk"}:
        size = 2500 if kind == "page" else 1000
        return text[index * size:(index + 1) * size] or "Location not found in extracted text."
    if kind == "section":
        marker = raw_index.lower()
        start = text.lower().find(marker)
        return text[start:start + 2500] if start >= 0 else "Section not found in extracted text."
    return text[:2500]


def _user_matters(user_id: str) -> dict[str, dict[str, Any]]:
    return _matters.setdefault(user_id, {})


class MatterCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    reference: str = ""
    description: str = ""


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    body: str = ""
    status: str = "open"


class AgentRun(BaseModel):
    matter_id: str
    prompt: str = Field(min_length=2, max_length=4000)
    context: list[str] = []


class ResearchRunRequest(BaseModel):
    query: str = Field(default="", max_length=4000)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)


class ResearchRunResponse(BaseModel):
    matter_id: str
    query: str
    verified: bool
    review_required: bool
    memo_title: str
    memo_text: str
    confidence: float
    saved_research: dict[str, Any] | None = None
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    source_mappings: list[dict[str, Any]] = Field(default_factory=list)
    rejected_claims: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


@router.post("/launch")
def create_launch_token(current_user: dict[str, str] = Depends(get_current_user)):
    token = uuid4().hex
    _launch_tokens[token] = (current_user["user_id"], datetime.now(timezone.utc) + timedelta(minutes=2))
    return {"launch_token": token, "expires_in": 120}


@router.post("/auth/exchange")
def exchange_launch_token(payload: dict[str, str]):
    token = payload.get("launch_token", "")
    entry = _launch_tokens.pop(token, None)
    if not entry or entry[1] < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Launch token is invalid or expired.")
    return {"access_token": create_access_token(entry[0]), "token_type": "bearer", "expires_in": 86400}


@router.get("/matters")
def list_matters(state: str = "active", current_user: dict[str, str] = Depends(get_current_user)):
    matters = list(_user_matters(current_user["user_id"]).values())
    return {"items": [m for m in matters if state == "all" or m["state"] == state]}


@router.post("/matters")
def create_matter(payload: MatterCreate, current_user: dict[str, str] = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    matter = {"id": uuid4().hex, "title": payload.title, "reference": payload.reference, "description": payload.description, "state": "active", "created_at": now, "updated_at": now, "tabs": {name: [] for name in ("parties", "hearings", "tasks", "notes", "timeline", "research", "drafts")}, "documents": []}
    _user_matters(current_user["user_id"])[matter["id"]] = matter
    _persist()
    return matter


def _matter(user_id: str, matter_id: str) -> dict[str, Any]:
    matter = _user_matters(user_id).get(matter_id)
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found.")
    return matter


@router.get("/matters/{matter_id}")
def get_matter(matter_id: str, current_user: dict[str, str] = Depends(get_current_user)):
    return _matter(current_user["user_id"], matter_id)


@router.patch("/matters/{matter_id}")
def update_matter(matter_id: str, payload: dict[str, Any], current_user: dict[str, str] = Depends(get_current_user)):
    matter = _matter(current_user["user_id"], matter_id)
    matter["state"] = "archived" if payload.get("state") == "archived" else matter["state"]
    matter["updated_at"] = datetime.now(timezone.utc).isoformat()
    _persist()
    return matter


@router.get("/matters/{matter_id}/{tab}")
def list_tab(matter_id: str, tab: str, current_user: dict[str, str] = Depends(get_current_user)):
    matter = _matter(current_user["user_id"], matter_id)
    if tab not in matter["tabs"]:
        raise HTTPException(status_code=404, detail="Unknown workspace tab.")
    return {"items": matter["tabs"][tab]}


@router.post("/matters/{matter_id}/{tab}")
def create_tab_item(matter_id: str, tab: str, payload: ItemCreate, current_user: dict[str, str] = Depends(get_current_user)):
    matter = _matter(current_user["user_id"], matter_id)
    if tab not in matter["tabs"]:
        raise HTTPException(status_code=404, detail="Unknown workspace tab.")
    item = {"id": uuid4().hex, "title": payload.title, "body": payload.body, "status": payload.status, "created_at": datetime.now(timezone.utc).isoformat()}
    matter["tabs"][tab].append(item)
    _persist()
    return item


@router.post("/matters/{matter_id}/documents")
async def upload_document(matter_id: str, file: UploadFile = File(...), current_user: dict[str, str] = Depends(get_current_user)):
    matter = _matter(current_user["user_id"], matter_id)
    content = await file.read()
    document = {"id": uuid4().hex, "name": file.filename or "Untitled document", "content_type": file.content_type or "application/octet-stream", "size": len(content), "text": content.decode("utf-8", errors="replace")[:100000], "uploaded_at": datetime.now(timezone.utc).isoformat()}
    matter["documents"].append(document)
    _persist()
    return {k: v for k, v in document.items() if k != "text"}


@router.get("/matters/{matter_id}/documents")
def list_documents(matter_id: str, current_user: dict[str, str] = Depends(get_current_user)):
    return {"items": [{k: v for k, v in d.items() if k != "text"} for d in _matter(current_user["user_id"], matter_id)["documents"]]}


@router.get("/matters/{matter_id}/documents/{document_id}")
def get_document(matter_id: str, document_id: str, location: str = "", current_user: dict[str, str] = Depends(get_current_user)):
    document = next((d for d in _matter(current_user["user_id"], matter_id)["documents"] if d["id"] == document_id), None)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {**document, "location": location, "anchor": _resolve_document_location(document["text"], location)}


@router.post("/matters/{matter_id}/documents/{document_id}/verify")
def verify_citation(matter_id: str, document_id: str, current_user: dict[str, str] = Depends(get_current_user)):
    matter = _matter(current_user["user_id"], matter_id)
    if not any(d["id"] == document_id for d in matter["documents"]):
        raise HTTPException(status_code=404, detail="Document not found.")
    key = f"{current_user['user_id']}:{matter_id}"
    _verified.setdefault(key, set()).add(document_id)
    _persist()
    return {"verified": True}


@router.post("/matters/{matter_id}/citations/verify")
def verify_any_citation(matter_id: str, payload: dict[str, str], current_user: dict[str, str] = Depends(get_current_user)):
    _matter(current_user["user_id"], matter_id)
    citation_id = payload.get("citation_id", "").strip()
    if not citation_id:
        raise HTTPException(status_code=422, detail="Citation id is required.")
    key = f"{current_user['user_id']}:{matter_id}"
    _verified.setdefault(key, set()).add(citation_id)
    _persist()
    return {"verified": True}


@router.get("/legal-sources")
def legal_sources(query: str, current_user: dict[str, str] = Depends(get_current_user)):
    return {"items": _legal_sources(query)}


@router.get("/legal-sources/{act_key}/{section_number}")
def legal_source(act_key: str, section_number: str, current_user: dict[str, str] = Depends(get_current_user)):
    source = next((item for item in _legal_sources(section_number + " " + act_key, limit=50000) if item.get("act_key") == act_key and str(item.get("section_number")) == section_number), None)
    if not source:
        raise HTTPException(status_code=404, detail="Legal source not found.")
    return source


@router.post("/agent/run")
def run_agent(payload: AgentRun, current_user: dict[str, str] = Depends(get_current_user)):
    matter = _matter(current_user["user_id"], payload.matter_id)
    evidence = [{"kind": "document", "id": d["id"], "label": d["name"], "location": "page:1", "excerpt": d["text"][:240] or "No extractable text."} for d in matter["documents"]]
    legal_evidence = _legal_sources(payload.prompt)
    evidence.extend({"kind": "legal", "id": f"{item['act_key']}:{item['section_number']}", "label": f"{item['act_name']} — {item['section']}", "location": f"section:{item['section_number']}", "excerpt": item.get("description", "")} for item in legal_evidence)
    if not evidence:
        return {"status": "abstained", "message": "No matter document or relevant legal source was found for this request.", "evidence": [], "review_required": False}
    source_text = "\n\n".join(f"SOURCE: {d['name']}\n{d['text'][:6000]}" for d in matter["documents"])
    legal_text = "\n".join(f"LEGAL SOURCE: {item['act_name']} {item['section']} — {item['description']}" for item in legal_evidence)
    try:
        answer, _ = generate_response(
            "You are a legal case agent. Answer only from the supplied matter sources. "
            "If the sources do not support an answer, explicitly abstain. Cite sources by their file name.\n\n"
            f"Question: {payload.prompt}\n\nMatter sources:\n{source_text}\n\nLegal sources:\n{legal_text}",
            conversation_history=[],
        )
    except Exception:
        answer = "The Case Agent could not complete an LLM review. Review the listed source excerpts manually."
    return {"status": "complete", "answer": answer, "context": payload.context, "evidence": evidence, "review_required": True, "message": "Open and verify the cited sources before saving this research."}


@router.post("/matters/{matter_id}/research/save")
def save_research(matter_id: str, payload: ItemCreate, current_user: dict[str, str] = Depends(get_current_user)):
    matter = _matter(current_user["user_id"], matter_id)
    key = f"{current_user['user_id']}:{matter_id}"
    if not _verified.get(key):
        raise HTTPException(status_code=409, detail="Open and verify at least one citation before saving research.")
    item = {"id": uuid4().hex, "title": payload.title, "body": payload.body, "status": "verified", "created_at": datetime.now(timezone.utc).isoformat()}
    matter["tabs"]["research"].append(item)
    _persist()
    return item


@router.get("/matters/{matter_id}/research")
def list_research(matter_id: str, current_user: dict[str, str] = Depends(get_current_user)):
    try:
        research_items = db_client.list_matter_research(current_user["user_id"], matter_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": research_items}


@router.get("/matters/{matter_id}/next")
def next_command(matter_id: str, current_user: dict[str, str] = Depends(get_current_user)):
    return build_next_preview(current_user["user_id"], matter_id)


@router.post("/matters/{matter_id}/timeline/preview")
def timeline_preview(matter_id: str, current_user: dict[str, str] = Depends(get_current_user)):
    preview = build_timeline_preview(current_user["user_id"], matter_id)
    return _store_preview(current_user["user_id"], matter_id, "timeline", preview)


@router.post("/matters/{matter_id}/timeline/confirm")
def timeline_confirm(
    matter_id: str,
    payload: dict[str, Any],
    current_user: dict[str, str] = Depends(get_current_user),
):
    preview_token = str(payload.get("preview_token") or "").strip()
    if not preview_token:
        raise HTTPException(status_code=422, detail="preview_token is required.")
    if not bool(payload.get("confirmed", False)):
        raise HTTPException(status_code=409, detail="Timeline save requires explicit confirmation.")
    preview = _consume_preview(preview_token, current_user["user_id"], matter_id, "timeline")
    item = {
        "id": uuid4().hex,
        "title": preview.get("title", "Timeline"),
        "body": json.dumps(preview, ensure_ascii=False),
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _matter(current_user["user_id"], matter_id)["tabs"]["timeline"].append(item)
    _persist()
    return item


@router.post("/matters/{matter_id}/draft/preview")
def draft_preview(
    matter_id: str,
    payload: dict[str, Any],
    current_user: dict[str, str] = Depends(get_current_user),
):
    _require_advanced_commands()
    document_type = str(payload.get("document_type") or "written-statement")
    document_type_label = str(payload.get("document_type_label") or document_type.replace("-", " ").title())
    case_details = str(payload.get("case_details") or "")
    draft_text, tokens_used = build_draft_preview(
        current_user["user_id"],
        matter_id,
        document_type=document_type,
        document_type_label=document_type_label,
        case_details=case_details,
        party_details=str(payload.get("party_details") or ""),
        recipient_details=str(payload.get("recipient_details") or ""),
        relevant_info=str(payload.get("relevant_info") or ""),
        additional_info=str(payload.get("additional_info") or ""),
        structured_fields=dict(payload.get("structured_fields") or {}),
        structured_sections=list(payload.get("structured_sections") or []),
        skill_name=str(payload.get("skill_name") or ""),
        skill_prompt=str(payload.get("skill_prompt") or ""),
    )
    preview = {
        "document_type": document_type,
        "document_type_label": document_type_label,
        "draft_text": draft_text,
        "tokens_used": tokens_used,
    }
    return _store_preview(current_user["user_id"], matter_id, "draft", preview)


@router.post("/matters/{matter_id}/draft/confirm")
def draft_confirm(
    matter_id: str,
    payload: dict[str, Any],
    current_user: dict[str, str] = Depends(get_current_user),
):
    _require_advanced_commands()
    preview_token = str(payload.get("preview_token") or "").strip()
    if not preview_token:
        raise HTTPException(status_code=422, detail="preview_token is required.")
    if not bool(payload.get("confirmed", False)):
        raise HTTPException(status_code=409, detail="Draft save requires explicit confirmation.")
    preview = _consume_preview(preview_token, current_user["user_id"], matter_id, "draft")
    draft_parent_id = str(payload.get("draft_id") or "").strip()
    if draft_parent_id:
        existing = next(
            (row for row in db_client.list_matter_drafts(current_user["user_id"], matter_id) if row["draft_id"] == draft_parent_id),
            None,
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Draft not found.")
    else:
        parent = db_client.create_matter_draft(
            user_id=current_user["user_id"],
            matter_id=matter_id,
            title=str(payload.get("title") or preview.get("document_type_label") or "Draft"),
            document_type=str(payload.get("document_type") or preview.get("document_type") or "document"),
        )
        draft_parent_id = parent["draft_id"]
    citations_payload = list(payload.get("citations") or [])
    verified_source_ids = _verified_research_source_ids(current_user["user_id"], matter_id)
    validated_citations: list[dict[str, Any]] = []
    for citation in citations_payload:
        source_id = str((citation or {}).get("source_id") or "").strip()
        if not source_id:
            raise HTTPException(status_code=422, detail="Each citation must include a source_id.")
        if source_id not in verified_source_ids:
            raise HTTPException(status_code=409, detail=f"Unknown or unverified source_id: {source_id}")
        validated_citations.append(
            {
                **citation,
                "source_id": source_id,
            }
        )
    if not validated_citations:
        validated_citations = [{"source_id": source_id} for source_id in sorted(verified_source_ids)]
    version = db_client.create_draft_version(
        user_id=current_user["user_id"],
        matter_id=matter_id,
        draft_id=draft_parent_id,
        content=str(preview.get("draft_text") or ""),
        citations=validated_citations,
    )
    return {"draft_id": draft_parent_id, "version": version, "preview": preview}


@router.get("/matters/{matter_id}/drafts/{draft_id}/versions")
def list_draft_versions_route(
    matter_id: str,
    draft_id: str,
    current_user: dict[str, str] = Depends(get_current_user),
):
    return {"items": db_client.list_draft_versions(current_user["user_id"], matter_id, draft_id)}


@router.get("/matters/{matter_id}/drafts/{draft_id}/versions/compare")
def compare_draft_versions_route(
    matter_id: str,
    draft_id: str,
    left_version: int,
    right_version: int,
    current_user: dict[str, str] = Depends(get_current_user),
):
    versions = db_client.list_draft_versions(current_user["user_id"], matter_id, draft_id)
    left = next((item for item in versions if int(item.get("version_number", 0)) == int(left_version)), None)
    right = next((item for item in versions if int(item.get("version_number", 0)) == int(right_version)), None)
    if not left or not right:
        raise HTTPException(status_code=404, detail="Draft version not found.")
    return {
        "left_version": left_version,
        "right_version": right_version,
        "diff": compare_text_versions(str(left.get("content") or ""), str(right.get("content") or "")),
    }


@router.post("/matters/{matter_id}/review")
def review_command(
    matter_id: str,
    payload: dict[str, Any],
    current_user: dict[str, str] = Depends(get_current_user),
):
    _require_advanced_commands()
    source_type = str(payload.get("source_type") or "document")
    source_id = str(payload.get("source_id") or "")
    query = str(payload.get("query") or "")
    if not source_id:
        raise HTTPException(status_code=422, detail="source_id is required.")
    return build_review_report(
        current_user["user_id"],
        matter_id,
        source_type=source_type,
        source_id=source_id,
        query=query,
    )


@router.post("/matters/{matter_id}/brief/preview")
def brief_preview(matter_id: str, current_user: dict[str, str] = Depends(get_current_user)):
    _require_advanced_commands()
    preview = build_brief_preview(current_user["user_id"], matter_id)
    return _store_preview(current_user["user_id"], matter_id, "brief", preview)


@router.post("/matters/{matter_id}/brief/confirm")
def brief_confirm(
    matter_id: str,
    payload: dict[str, Any],
    current_user: dict[str, str] = Depends(get_current_user),
):
    _require_advanced_commands()
    preview_token = str(payload.get("preview_token") or "").strip()
    if not preview_token:
        raise HTTPException(status_code=422, detail="preview_token is required.")
    if not bool(payload.get("confirmed", False)):
        raise HTTPException(status_code=409, detail="Brief save requires explicit confirmation.")
    preview = _consume_preview(preview_token, current_user["user_id"], matter_id, "brief")
    draft = db_client.create_matter_draft(
        user_id=current_user["user_id"],
        matter_id=matter_id,
        title=str(preview.get("title") or "Hearing Brief"),
        document_type="brief",
    )
    version = db_client.create_draft_version(
        user_id=current_user["user_id"],
        matter_id=matter_id,
        draft_id=draft["draft_id"],
        content=str(preview.get("brief_text") or ""),
        citations=[],
    )
    return {"draft_id": draft["draft_id"], "version": version, "preview": preview}


@router.post("/matters/{matter_id}/diary/preview")
def diary_preview(
    matter_id: str,
    payload: dict[str, Any],
    current_user: dict[str, str] = Depends(get_current_user),
):
    _require_advanced_commands()
    preview = {
        "date": str(payload.get("date") or ""),
        "duration": str(payload.get("duration") or ""),
        "category": str(payload.get("category") or ""),
        "description": str(payload.get("description") or ""),
        "follow_up_task": str(payload.get("follow_up_task") or ""),
    }
    return _store_preview(current_user["user_id"], matter_id, "diary", preview)


@router.post("/matters/{matter_id}/diary/confirm")
def diary_confirm(
    matter_id: str,
    payload: dict[str, Any],
    current_user: dict[str, str] = Depends(get_current_user),
):
    _require_advanced_commands()
    preview_token = str(payload.get("preview_token") or "").strip()
    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if not preview_token:
        raise HTTPException(status_code=422, detail="preview_token is required.")
    if not idempotency_key:
        raise HTTPException(status_code=422, detail="idempotency_key is required.")
    ledger_key = f"{current_user['user_id']}:{matter_id}:diary:{idempotency_key}"
    if ledger_key in _idempotency:
        return {"ok": True, "duplicate": True, "result_id": _idempotency[ledger_key]}
    preview = _consume_preview(preview_token, current_user["user_id"], matter_id, "diary")
    entry = db_client.create_matter_task(
        user_id=current_user["user_id"],
        matter_id=matter_id,
        title=f"Diary: {preview.get('category') or 'Entry'}",
        description=f"{preview.get('date')} | {preview.get('duration')} | {preview.get('description')} | Follow-up: {preview.get('follow_up_task')}",
        due_at=None,
    )
    _idempotency[ledger_key] = entry.get("task_id", "")
    _persist()
    return {"ok": True, "result": entry, "preview": preview}


@router.post("/matters/{matter_id}/research", response_model=ResearchRunResponse)
def run_research_endpoint(
    matter_id: str,
    payload: ResearchRunRequest,
    current_user: dict[str, str] = Depends(get_current_user),
):
    try:
        from ..services.research_service import run_research

        result = run_research(
            user_id=current_user["user_id"],
            matter_id=matter_id,
            query=payload.query.strip() or _matter(current_user["user_id"], matter_id)["title"],
            conversation_history=payload.conversation_history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ResearchRunResponse(
        matter_id=matter_id,
        query=result.query,
        verified=result.verification.verified,
        review_required=result.verification.review_required,
        memo_title=result.verification.memo_title,
        memo_text=result.verification.memo_text,
        confidence=result.verification.confidence,
        saved_research=result.saved_research,
        evidence_sources=[source.to_dict() for source in result.evidence_sources],
        claims=[{
            "claim_id": claim.claim_id,
            "text": claim.text,
            "source_ids": claim.source_ids,
            "source_locations": claim.source_locations,
            "material": claim.material,
            "confidence": claim.confidence,
            "claim_type": claim.claim_type,
        } for claim in result.verification.claims],
        source_mappings=[
            {
                "source_id": mapping.source_id,
                "claim_ids": mapping.claim_ids,
                "support": mapping.support,
            }
            for mapping in result.verification.source_mappings
        ],
        rejected_claims=result.verification.rejected_claims,
        notes=result.verification.notes,
    )


@router.post("/agent/feedback")
def agent_feedback(payload: dict[str, Any], current_user: dict[str, str] = Depends(get_current_user)):
    value = str(payload.get("value") or "").strip()
    category = str(payload.get("category") or payload.get("feedback_category") or "").strip().lower()
    artifact_type = str(payload.get("artifact_type") or payload.get("command_type") or "research").strip().lower()
    allowed_categories = {"citation issue", "missing authority", "source issue", "drafting issue"}
    allowed_artifacts = {"research", "draft", "review", "brief"}
    if value not in {"useful", "not_useful", ""}:
        raise HTTPException(status_code=422, detail="Feedback value must be useful or not_useful.")
    if category and category not in allowed_categories:
        raise HTTPException(status_code=422, detail="Unsupported feedback category.")
    if artifact_type and artifact_type not in allowed_artifacts:
        raise HTTPException(status_code=422, detail="Unsupported feedback artifact type.")
    record = {
        "value": value or None,
        "category": category or None,
        "artifact_type": artifact_type,
        "matter_id": payload.get("matter_id"),
        "research_id": payload.get("research_id"),
        "draft_id": payload.get("draft_id"),
        "comment": payload.get("comment", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _feedback.setdefault(current_user["user_id"], []).append(record)
    _persist()
    return {"ok": True, "feedback": record}
