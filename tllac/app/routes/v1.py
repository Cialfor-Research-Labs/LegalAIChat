from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

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
        return {"matters": {}, "feedback": {}, "verified": {}}


_store = _load_store()
_matters: dict[str, dict[str, dict[str, Any]]] = _store["matters"]
_feedback: dict[str, list[dict[str, Any]]] = _store["feedback"]
_verified: dict[str, set[str]] = {key: set(value) for key, value in _store.get("verified", {}).items()}


def _persist() -> None:
    with _store_lock:
        _store_path.write_text(json.dumps({"matters": _matters, "feedback": _feedback, "verified": {key: list(value) for key, value in _verified.items()}}, ensure_ascii=False), encoding="utf-8")


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


@router.post("/agent/feedback")
def agent_feedback(payload: dict[str, Any], current_user: dict[str, str] = Depends(get_current_user)):
    value = payload.get("value")
    if value not in {"useful", "not_useful"}:
        raise HTTPException(status_code=422, detail="Feedback value must be useful or not_useful.")
    _feedback.setdefault(current_user["user_id"], []).append({"value": value, "matter_id": payload.get("matter_id"), "created_at": datetime.now(timezone.utc).isoformat()})
    _persist()
    return {"ok": True}
