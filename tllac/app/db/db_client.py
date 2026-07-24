"""
Postgres-backed chat and auth persistence for TLLAC.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any, Optional
from uuid import uuid4
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("tllac.db")

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / "tllac" / ".env")


class DBClient:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url or self._resolve_database_url()

        self._encryption = Fernet(self._build_fernet_key())
        self._lock = Lock()
        self._backend = "memory"
        self._init_memory_store()

        if self._db_url:
            try:
                self._ensure_schema()
                self._backend = "postgres"
                logger.info("DBClient initialized with Postgres.")
                return
            except Exception as exc:
                logger.warning(
                    "Postgres storage is unavailable (%s). Falling back to local in-memory storage.",
                    exc,
                )

        logger.info("DBClient initialized with local fallback storage.")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _now_iso() -> str:
        return DBClient._now().isoformat()

    @staticmethod
    def _build_fernet_key() -> bytes:
        key = os.getenv("CHAT_ENCRYPTION_KEY", "").strip()
        if key:
            return key.encode("utf-8")

        secret = os.getenv("APP_SECRET_KEY", "").strip()
        if not secret:
            raise RuntimeError(
                "CHAT_ENCRYPTION_KEY or APP_SECRET_KEY is required for encrypted chat storage."
            )

        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    @staticmethod
    def _looks_placeholder_database_url(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or "user:password@host" in normalized or normalized.endswith("@host:5432/legalaichat")

    def _build_database_url_from_parts(self) -> str | None:
        database_name = os.getenv("POSTGRES_DB", "").strip() or "legalaichat"
        app_user = os.getenv("POSTGRES_APP_USER", "").strip()
        app_password = os.getenv("POSTGRES_APP_PASSWORD", "").strip()
        host = os.getenv("POSTGRES_HOST", "").strip() or "localhost"
        port = os.getenv("POSTGRES_PORT", "").strip() or "5432"

        if not app_user or not app_password:
            return None

        return (
            f"postgresql://{quote(app_user)}:{quote(app_password)}"
            f"@{host}:{port}/{quote(database_name)}"
        )

    def _resolve_database_url(self) -> str | None:
        direct = os.getenv("DATABASE_URL", "").strip()
        if direct and not self._looks_placeholder_database_url(direct):
            return direct

        fallback = os.getenv("POSTGRES_URL", "").strip()
        if fallback and not self._looks_placeholder_database_url(fallback):
            return fallback

        return self._build_database_url_from_parts()

    def _init_memory_store(self) -> None:
        self._memory_users: dict[str, dict[str, Any]] = {}
        self._memory_sessions: dict[str, dict[str, Any]] = {}
        self._memory_artifacts: dict[str, dict[str, Any]] = {}

    def _connect(self):
        return psycopg.connect(self._db_url, row_factory=dict_row)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_users (
                        user_id UUID PRIMARY KEY,
                        email TEXT NOT NULL UNIQUE,
                        full_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        session_id UUID PRIMARY KEY,
                        user_id UUID NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
                        title TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );

                    CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated
                    ON chat_sessions (user_id, updated_at DESC);

                    CREATE TABLE IF NOT EXISTS chat_messages (
                        message_id UUID PRIMARY KEY,
                        session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                        role TEXT NOT NULL,
                        encrypted_content BYTEA NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );

                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
                    ON chat_messages (session_id, created_at ASC);

                    CREATE TABLE IF NOT EXISTS generated_artifacts (
                        artifact_id UUID PRIMARY KEY,
                        user_id UUID NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
                        artifact_type TEXT NOT NULL,
                        title TEXT NOT NULL,
                        encrypted_input BYTEA NOT NULL,
                        encrypted_output BYTEA NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );

                    CREATE INDEX IF NOT EXISTS idx_generated_artifacts_user_type_updated
                    ON generated_artifacts (user_id, artifact_type, updated_at DESC);
                    """
                )
            conn.commit()

    def _encrypt(self, content: str) -> bytes:
        return self._encryption.encrypt(content.encode("utf-8"))

    def _decrypt(self, payload: bytes) -> str:
        try:
            return self._encryption.decrypt(payload).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Stored chat message could not be decrypted.") from exc

    @staticmethod
    def _make_password_hash(password: str) -> str:
        salt = os.urandom(16)
        iterations = 120000
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return "pbkdf2_sha256${}${}${}".format(
            iterations,
            base64.b64encode(salt).decode("utf-8"),
            base64.b64encode(digest).decode("utf-8"),
        )

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            algorithm, iteration_text, salt_b64, digest_b64 = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(digest_b64)
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                int(iteration_text),
            )
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False

    def create_user(self, email: str, full_name: str, password: str) -> dict[str, str]:
        normalized_email = email.strip().lower()
        user_id = str(uuid4())
        password_hash = self._make_password_hash(password)
        if self._backend != "postgres":
            if any(user["email"] == normalized_email for user in self._memory_users.values()):
                raise ValueError("An account with this email already exists.")
            user = {
                "user_id": user_id,
                "email": normalized_email,
                "full_name": full_name.strip(),
                "password_hash": password_hash,
                "created_at": self._now(),
                "updated_at": self._now(),
            }
            self._memory_users[user_id] = user
            return {"user_id": user_id, "email": normalized_email, "full_name": full_name.strip()}

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM app_users WHERE email = %s", (normalized_email,))
                if cur.fetchone():
                    raise ValueError("An account with this email already exists.")
                cur.execute(
                    """
                    INSERT INTO app_users (user_id, email, full_name, password_hash)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, normalized_email, full_name.strip(), password_hash),
                )
            conn.commit()
        return {"user_id": user_id, "email": normalized_email, "full_name": full_name.strip()}

    def authenticate_user(self, email: str, password: str) -> Optional[dict[str, str]]:
        normalized_email = email.strip().lower()
        if self._backend != "postgres":
            row = next((user for user in self._memory_users.values() if user["email"] == normalized_email), None)
            if not row or not self._verify_password(password, row["password_hash"]):
                return None
            return {
                "user_id": str(row["user_id"]),
                "email": row["email"],
                "full_name": row["full_name"],
            }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, email, full_name, password_hash
                    FROM app_users
                    WHERE email = %s
                    """,
                    (normalized_email,),
                )
                row = cur.fetchone()
        if not row or not self._verify_password(password, row["password_hash"]):
            return None
        return {
            "user_id": str(row["user_id"]),
            "email": row["email"],
            "full_name": row["full_name"],
        }

    def get_user_by_id(self, user_id: str) -> Optional[dict[str, str]]:
        if self._backend != "postgres":
            row = self._memory_users.get(user_id)
            if not row:
                return None
            return {
                "user_id": str(row["user_id"]),
                "email": row["email"],
                "full_name": row["full_name"],
            }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, email, full_name FROM app_users WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return {
            "user_id": str(row["user_id"]),
            "email": row["email"],
            "full_name": row["full_name"],
        }

    def ensure_session(self, user_id: str, session_id: Optional[str], title_hint: str = "") -> str:
        resolved = session_id or str(uuid4())
        title = (title_hint or "New Chat").strip()[:80] or "New Chat"
        if self._backend != "postgres":
            if user_id not in self._memory_users:
                raise ValueError("Session does not belong to the authenticated user.")
            session = self._memory_sessions.get(resolved)
            if session and session["user_id"] != user_id:
                raise ValueError("Session does not belong to the authenticated user.")
            if not session:
                self._memory_sessions[resolved] = {
                    "session_id": resolved,
                    "user_id": user_id,
                    "title": title,
                    "created_at": self._now(),
                    "updated_at": self._now(),
                    "messages": [],
                }
            else:
                if session["title"] == "New Chat" and title != "New Chat":
                    session["title"] = title
                session["updated_at"] = self._now()
            return resolved

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_sessions (session_id, user_id, title, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT (session_id) DO UPDATE
                    SET updated_at = NOW(),
                        title = CASE
                            WHEN chat_sessions.title = 'New Chat' AND EXCLUDED.title <> 'New Chat'
                            THEN EXCLUDED.title
                            ELSE chat_sessions.title
                        END
                    WHERE chat_sessions.user_id = EXCLUDED.user_id
                    RETURNING session_id
                    """,
                    (resolved, user_id, title),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Session does not belong to the authenticated user.")
            conn.commit()
        return str(row["session_id"])

    def append_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
        encrypted = self._encrypt(content)
        if self._backend != "postgres":
            session = self._memory_sessions.get(session_id)
            if not session or session["user_id"] != user_id:
                raise ValueError("Session does not belong to the authenticated user.")
            if session["title"] == "New Chat" and role == "user" and content.strip():
                session["title"] = content.strip()[:80]
            session["messages"].append(
                {
                    "message_id": str(uuid4()),
                    "role": role,
                    "encrypted_content": encrypted,
                    "created_at": self._now(),
                }
            )
            session["updated_at"] = self._now()
            return

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT title FROM chat_sessions WHERE session_id = %s AND user_id = %s",
                    (session_id, user_id),
                )
                session = cur.fetchone()
                if not session:
                    raise ValueError("Session does not belong to the authenticated user.")
                if session["title"] == "New Chat" and role == "user" and content.strip():
                    cur.execute(
                        "UPDATE chat_sessions SET title = %s WHERE session_id = %s",
                        (content.strip()[:80], session_id),
                    )
                cur.execute(
                    """
                    INSERT INTO chat_messages (message_id, session_id, role, encrypted_content, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (str(uuid4()), session_id, role, encrypted),
                )
                cur.execute(
                    "UPDATE chat_sessions SET updated_at = NOW() WHERE session_id = %s",
                    (session_id,),
                )
            conn.commit()

    def get_messages(
        self,
        user_id: str,
        session_id: Optional[str],
        limit: Optional[int] = None,
    ) -> list[dict[str, str]]:
        if not session_id:
            return []
        if self._backend != "postgres":
            session = self._memory_sessions.get(session_id)
            if not session or session["user_id"] != user_id:
                return []
            rows = session["messages"][:]
            if limit:
                rows = rows[:limit]
            return [
                {
                    "id": str(row["message_id"]),
                    "role": str(row["role"]),
                    "content": self._decrypt(bytes(row["encrypted_content"])),
                    "timestamp": row["created_at"].astimezone(timezone.utc).isoformat(),
                }
                for row in rows
            ]

        query = """
            SELECT m.message_id, m.role, m.encrypted_content, m.created_at
            FROM chat_messages m
            JOIN chat_sessions s ON s.session_id = m.session_id
            WHERE s.session_id = %s AND s.user_id = %s
            ORDER BY m.created_at ASC
        """
        params: list[Any] = [session_id, user_id]
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        return [
            {
                "id": str(row["message_id"]),
                "role": str(row["role"]),
                "content": self._decrypt(bytes(row["encrypted_content"])),
                "timestamp": row["created_at"].astimezone(timezone.utc).isoformat(),
            }
            for row in rows
        ]

    def list_sessions(self, user_id: str) -> list[dict[str, str]]:
        if self._backend != "postgres":
            rows = [
                session
                for session in self._memory_sessions.values()
                if session["user_id"] == user_id
            ]
            rows.sort(key=lambda item: item["updated_at"], reverse=True)
            return [
                {
                    "session_id": str(row["session_id"]),
                    "title": row["title"],
                    "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
                    "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
                }
                for row in rows
            ]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, title, created_at, updated_at
                    FROM chat_sessions
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
        return [
            {
                "session_id": str(row["session_id"]),
                "title": row["title"],
                "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
                "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
            }
            for row in rows
        ]

    def get_session_messages(self, user_id: str, session_id: str) -> dict[str, Any]:
        if self._backend != "postgres":
            row = self._memory_sessions.get(session_id)
            if not row or row["user_id"] != user_id:
                raise ValueError("Session not found.")
            return {
                "session_id": str(row["session_id"]),
                "title": row["title"],
                "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
                "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
                "messages": self.get_messages(user_id, session_id),
            }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, title, created_at, updated_at
                    FROM chat_sessions
                    WHERE session_id = %s AND user_id = %s
                    """,
                    (session_id, user_id),
                )
                row = cur.fetchone()
        if not row:
            raise ValueError("Session not found.")
        return {
            "session_id": str(row["session_id"]),
            "title": row["title"],
            "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
            "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
            "messages": self.get_messages(user_id, session_id),
        }

    def save_generated_artifact(
        self,
        *,
        user_id: str,
        artifact_type: str,
        title: str,
        input_payload: dict[str, Any],
        output_text: str,
        artifact_id: str | None = None,
    ) -> str:
        resolved_artifact_id = artifact_id or str(uuid4())
        encrypted_input = self._encrypt(json.dumps(input_payload))
        encrypted_output = self._encrypt(output_text)
        if self._backend != "postgres":
            self._memory_artifacts[resolved_artifact_id] = {
                "artifact_id": resolved_artifact_id,
                "user_id": user_id,
                "artifact_type": artifact_type,
                "title": title.strip()[:120] or artifact_type,
                "encrypted_input": encrypted_input,
                "encrypted_output": encrypted_output,
                "created_at": self._now(),
                "updated_at": self._now(),
            }
            return resolved_artifact_id

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO generated_artifacts (
                        artifact_id,
                        user_id,
                        artifact_type,
                        title,
                        encrypted_input,
                        encrypted_output,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING artifact_id
                    """,
                    (
                        resolved_artifact_id,
                        user_id,
                        artifact_type,
                        title.strip()[:120] or artifact_type,
                        encrypted_input,
                        encrypted_output,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return str(row["artifact_id"])

    def list_generated_artifacts(self, user_id: str, artifact_type: str) -> list[dict[str, str]]:
        if self._backend != "postgres":
            rows = [
                artifact
                for artifact in self._memory_artifacts.values()
                if artifact["user_id"] == user_id and artifact["artifact_type"] == artifact_type
            ]
            rows.sort(key=lambda item: item["updated_at"], reverse=True)
            return [
                {
                    "artifact_id": str(row["artifact_id"]),
                    "title": row["title"],
                    "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
                    "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
                }
                for row in rows
            ]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT artifact_id, title, created_at, updated_at
                    FROM generated_artifacts
                    WHERE user_id = %s AND artifact_type = %s
                    ORDER BY updated_at DESC
                    """,
                    (user_id, artifact_type),
                )
                rows = cur.fetchall()
        return [
            {
                "artifact_id": str(row["artifact_id"]),
                "title": row["title"],
                "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
                "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
            }
            for row in rows
        ]

    def get_generated_artifact(self, user_id: str, artifact_id: str, artifact_type: str) -> dict[str, Any]:
        if self._backend != "postgres":
            row = self._memory_artifacts.get(artifact_id)
            if not row or row["user_id"] != user_id or row["artifact_type"] != artifact_type:
                raise ValueError("Generated item not found.")
            return {
                "artifact_id": str(row["artifact_id"]),
                "title": row["title"],
                "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
                "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
                "input_payload": json.loads(self._decrypt(bytes(row["encrypted_input"]))),
                "output_text": self._decrypt(bytes(row["encrypted_output"])),
            }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT artifact_id, title, encrypted_input, encrypted_output, created_at, updated_at
                    FROM generated_artifacts
                    WHERE artifact_id = %s AND user_id = %s AND artifact_type = %s
                    """,
                    (artifact_id, user_id, artifact_type),
                )
                row = cur.fetchone()
        if not row:
            raise ValueError("Generated item not found.")
        return {
            "artifact_id": str(row["artifact_id"]),
            "title": row["title"],
            "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
            "updated_at": row["updated_at"].astimezone(timezone.utc).isoformat(),
            "input_payload": json.loads(self._decrypt(bytes(row["encrypted_input"]))),
            "output_text": self._decrypt(bytes(row["encrypted_output"])),
        }


db_client = DBClient()
