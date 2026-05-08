"""
Lightweight local chat-memory client.

This keeps recent chat sessions in a small JSON file so the backend can
remember previous turns without requiring a separate database service.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger("tllac.db")


class DBClient:
    """Minimal local session store."""

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url
        self._connection = None
        self._lock = Lock()
        self._storage_path = Path(__file__).resolve().parent / "chat_memory.json"
        if not self._storage_path.exists():
            self._storage_path.write_text(json.dumps({"sessions": {}}, indent=2), encoding="utf-8")
        logger.info(
            "DBClient initialized (db_url=%s).",
            db_url or f"local file store at {self._storage_path}",
        )

    def get_connection(self):
        """Return a database connection (None if no DB configured)."""
        return self._connection

    def is_connected(self) -> bool:
        """Check whether a database connection is active."""
        return self._connection is not None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _read_store(self) -> dict[str, Any]:
        try:
            raw = self._storage_path.read_text(encoding="utf-8").strip()
            if not raw:
                return {"sessions": {}}
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {"sessions": {}}
            data.setdefault("sessions", {})
            return data
        except Exception:
            logger.exception("Failed to read chat memory store. Reinitializing.")
            return {"sessions": {}}

    def _write_store(self, store: dict[str, Any]) -> None:
        self._storage_path.write_text(json.dumps(store, indent=2), encoding="utf-8")

    def ensure_session(self, session_id: Optional[str], title_hint: str = "") -> str:
        with self._lock:
            store = self._read_store()
            sessions = store["sessions"]
            resolved = session_id or str(uuid4())
            if resolved not in sessions:
                sessions[resolved] = {
                    "session_id": resolved,
                    "title": (title_hint or "New Chat").strip()[:80],
                    "created_at": self._now_iso(),
                    "updated_at": self._now_iso(),
                    "messages": [],
                }
            elif title_hint and sessions[resolved].get("title", "New Chat") == "New Chat":
                sessions[resolved]["title"] = title_hint.strip()[:80]
            sessions[resolved]["updated_at"] = self._now_iso()
            self._write_store(store)
            return resolved

    def append_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            store = self._read_store()
            sessions = store["sessions"]
            session = sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "title": "New Chat",
                    "created_at": self._now_iso(),
                    "updated_at": self._now_iso(),
                    "messages": [],
                },
            )
            if session.get("title") == "New Chat" and role == "user" and content.strip():
                session["title"] = content.strip()[:80]
            session["messages"].append(
                {
                    "role": role,
                    "content": content,
                    "timestamp": self._now_iso(),
                }
            )
            session["updated_at"] = self._now_iso()
            self._write_store(store)

    def get_recent_messages(self, session_id: Optional[str], limit: int = 8) -> list[dict[str, str]]:
        if not session_id:
            return []
        with self._lock:
            store = self._read_store()
            session = store["sessions"].get(session_id) or {}
            messages = session.get("messages") or []
            trimmed = messages[-limit:]
            return [
                {
                    "role": str(message.get("role", "")),
                    "content": str(message.get("content", "")),
                }
                for message in trimmed
                if message.get("role") and message.get("content")
            ]

    def get_messages(self, session_id: Optional[str], limit: Optional[int] = None) -> list[dict[str, str]]:
        if not session_id:
            return []
        with self._lock:
            store = self._read_store()
            session = store["sessions"].get(session_id) or {}
            messages = session.get("messages") or []
            selected = messages[-limit:] if limit else messages
            return [
                {
                    "role": str(message.get("role", "")),
                    "content": str(message.get("content", "")),
                }
                for message in selected
                if message.get("role") and message.get("content")
            ]


db_client = DBClient()
