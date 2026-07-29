"""V1-only matter and agent persistence for the existing DBClient."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb


_JSON_FIELDS = {
    "metadata",
    "details",
    "evidence",
    "citations",
    "context_snapshot",
    "input_payload",
    "output_payload",
}

_RELATED_TABLES: dict[str, tuple[str, str, str]] = {
    "party": ("matter_parties", "party_id", "created_at"),
    "hearing": ("matter_hearings", "hearing_id", "hearing_at"),
    "task": ("matter_tasks", "task_id", "due_at"),
    "note": ("matter_notes", "note_id", "created_at"),
    "event": ("matter_events", "event_id", "event_at"),
    "document": ("matter_documents", "document_id", "created_at"),
    "research": ("matter_research", "research_id", "updated_at"),
}


def _json_value(value: Any) -> Any:
    return Jsonb(value) if isinstance(value, (dict, list)) else value


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize_value(value) for key, value in row.items()}


class V1MatterPersistenceMixin:
    """Persistence methods used only by the V1 matter workspace and agents."""

    def _init_v1_memory_store(self) -> None:
        self._memory_v1_tables: dict[str, dict[str, dict[str, Any]]] = {
            "matters": {},
            "matter_parties": {},
            "matter_hearings": {},
            "matter_tasks": {},
            "matter_notes": {},
            "matter_events": {},
            "matter_documents": {},
            "matter_research": {},
            "matter_drafts": {},
            "draft_versions": {},
            "agent_runs": {},
            "agent_tool_calls": {},
            "agent_feedback": {},
        }

    def _apply_v1_migrations(self, cursor: Any) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS v1_schema_migrations (
                version TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        migrations_path = Path(__file__).resolve().parent / "migrations"
        for migration_path in sorted(migrations_path.glob("*.sql")):
            version = migration_path.stem
            sql = migration_path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            cursor.execute(
                "SELECT checksum FROM v1_schema_migrations WHERE version = %s",
                (version,),
            )
            applied = cursor.fetchone()
            if applied:
                if applied["checksum"] != checksum:
                    raise RuntimeError(
                        f"Applied V1 migration {version} does not match its checked-in checksum."
                    )
                continue
            cursor.execute(sql)
            cursor.execute(
                """
                INSERT INTO v1_schema_migrations (version, checksum)
                VALUES (%s, %s)
                """,
                (version, checksum),
            )

    def _v1_assert_matter_owned(
        self,
        user_id: str,
        matter_id: str,
        *,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        if self._backend != "postgres":
            row = self._memory_v1_tables["matters"].get(matter_id)
            if (
                not row
                or row["user_id"] != user_id
                or (row["is_archived"] and not include_archived)
            ):
                raise ValueError("Matter not found.")
            return row

        archived_clause = "" if include_archived else "AND is_archived = FALSE"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT *
                    FROM matters
                    WHERE user_id = %s AND matter_id = %s
                    {archived_clause}
                    """,
                    (user_id, matter_id),
                )
                row = cur.fetchone()
        if not row:
            raise ValueError("Matter not found.")
        return row

    def create_matter(
        self,
        *,
        user_id: str,
        title: str,
        description: str = "",
        case_number: str | None = None,
        court: str | None = None,
        jurisdiction: str | None = None,
        stage: str | None = None,
        status: str = "open",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        matter_id = str(uuid4())
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Matter title is required.")
        if self._backend != "postgres":
            if user_id not in self._memory_users:
                raise ValueError("User not found.")
            now = self._now()
            row = {
                "matter_id": matter_id,
                "user_id": user_id,
                "title": normalized_title,
                "description": description,
                "case_number": case_number,
                "court": court,
                "jurisdiction": jurisdiction,
                "stage": stage,
                "status": status,
                "metadata": metadata or {},
                "is_archived": False,
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self._memory_v1_tables["matters"][matter_id] = row
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO matters (
                        matter_id, user_id, title, description, case_number,
                        court, jurisdiction, stage, status, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        matter_id,
                        user_id,
                        normalized_title,
                        description,
                        case_number,
                        court,
                        jurisdiction,
                        stage,
                        status,
                        Jsonb(metadata or {}),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_row(row)

    def get_matter(
        self,
        user_id: str,
        matter_id: str,
        *,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        return _serialize_row(
            self._v1_assert_matter_owned(
                user_id,
                matter_id,
                include_archived=include_archived,
            )
        )

    def list_matters(
        self,
        user_id: str,
        *,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        if self._backend != "postgres":
            rows = [
                row
                for row in self._memory_v1_tables["matters"].values()
                if row["user_id"] == user_id
                and (include_archived or not row["is_archived"])
            ]
            rows.sort(key=lambda item: item["updated_at"], reverse=True)
            return [_serialize_row(row) for row in rows]

        archived_clause = "" if include_archived else "AND is_archived = FALSE"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT *
                    FROM matters
                    WHERE user_id = %s
                    {archived_clause}
                    ORDER BY updated_at DESC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
        return [_serialize_row(row) for row in rows]

    def update_matter(
        self,
        *,
        user_id: str,
        matter_id: str,
        **changes: Any,
    ) -> dict[str, Any]:
        allowed = {
            "title",
            "description",
            "case_number",
            "court",
            "jurisdiction",
            "stage",
            "status",
            "metadata",
        }
        values = {key: value for key, value in changes.items() if key in allowed}
        if not values:
            return self.get_matter(user_id, matter_id)
        if "title" in values and not str(values["title"]).strip():
            raise ValueError("Matter title is required.")
        self._v1_assert_matter_owned(user_id, matter_id)

        if self._backend != "postgres":
            row = self._memory_v1_tables["matters"][matter_id]
            row.update(values)
            row["updated_at"] = self._now()
            return _serialize_row(row)

        assignments = ", ".join(f"{column} = %s" for column in values)
        params = [
            Jsonb(value) if key == "metadata" else value
            for key, value in values.items()
        ]
        params.extend([user_id, matter_id])
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE matters
                    SET {assignments}
                    WHERE user_id = %s AND matter_id = %s AND is_archived = FALSE
                    RETURNING *
                    """,
                    params,
                )
                row = cur.fetchone()
            conn.commit()
        if not row:
            raise ValueError("Matter not found.")
        return _serialize_row(row)

    def archive_matter(self, *, user_id: str, matter_id: str) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id)
        if self._backend != "postgres":
            row = self._memory_v1_tables["matters"][matter_id]
            row["is_archived"] = True
            row["archived_at"] = self._now()
            row["updated_at"] = self._now()
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE matters
                    SET is_archived = TRUE, archived_at = NOW()
                    WHERE user_id = %s AND matter_id = %s AND is_archived = FALSE
                    RETURNING *
                    """,
                    (user_id, matter_id),
                )
                row = cur.fetchone()
            conn.commit()
        if not row:
            raise ValueError("Matter not found.")
        return _serialize_row(row)

    def _v1_create_related(
        self,
        *,
        kind: str,
        user_id: str,
        matter_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        table, id_field, _ = _RELATED_TABLES[kind]
        self._v1_assert_matter_owned(user_id, matter_id)
        record_id = str(uuid4())
        if self._backend != "postgres":
            now = self._now()
            row = {
                id_field: record_id,
                "user_id": user_id,
                "matter_id": matter_id,
                **fields,
                "is_archived": False,
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self._memory_v1_tables[table][record_id] = row
            return _serialize_row(row)

        columns = [id_field, "user_id", "matter_id", *fields.keys()]
        placeholders = ", ".join(["%s"] * len(columns))
        values = [record_id, user_id, matter_id]
        values.extend(
            Jsonb(value) if key in _JSON_FIELDS else value
            for key, value in fields.items()
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {table} ({", ".join(columns)})
                    VALUES ({placeholders})
                    RETURNING *
                    """,
                    values,
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_row(row)

    def _v1_list_related(
        self,
        *,
        kind: str,
        user_id: str,
        matter_id: str,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        table, _, order_field = _RELATED_TABLES[kind]
        self._v1_assert_matter_owned(
            user_id,
            matter_id,
            include_archived=include_archived,
        )
        if self._backend != "postgres":
            rows = [
                row
                for row in self._memory_v1_tables[table].values()
                if row["user_id"] == user_id
                and row["matter_id"] == matter_id
                and (include_archived or not row["is_archived"])
            ]
            rows.sort(
                key=lambda item: item.get(order_field) or item["created_at"],
                reverse=True,
            )
            return [_serialize_row(row) for row in rows]

        archived_clause = "" if include_archived else "AND is_archived = FALSE"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT *
                    FROM {table}
                    WHERE user_id = %s AND matter_id = %s
                    {archived_clause}
                    ORDER BY {order_field} DESC NULLS LAST, created_at DESC
                    """,
                    (user_id, matter_id),
                )
                rows = cur.fetchall()
        return [_serialize_row(row) for row in rows]

    def create_matter_party(
        self,
        *,
        user_id: str,
        matter_id: str,
        name: str,
        party_role: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._v1_create_related(
            kind="party",
            user_id=user_id,
            matter_id=matter_id,
            fields={"name": name, "party_role": party_role, "details": details or {}},
        )

    def list_matter_parties(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        return self._v1_list_related(kind="party", user_id=user_id, matter_id=matter_id)

    def create_matter_hearing(
        self,
        *,
        user_id: str,
        matter_id: str,
        title: str,
        hearing_at: datetime | str | None = None,
        court: str | None = None,
        status: str = "scheduled",
        notes: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._v1_create_related(
            kind="hearing",
            user_id=user_id,
            matter_id=matter_id,
            fields={
                "title": title,
                "hearing_at": hearing_at,
                "court": court,
                "status": status,
                "notes": notes,
                "details": details or {},
            },
        )

    def list_matter_hearings(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        return self._v1_list_related(kind="hearing", user_id=user_id, matter_id=matter_id)

    def create_matter_task(
        self,
        *,
        user_id: str,
        matter_id: str,
        title: str,
        description: str = "",
        due_at: datetime | str | None = None,
        status: str = "open",
        priority: str = "normal",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._v1_create_related(
            kind="task",
            user_id=user_id,
            matter_id=matter_id,
            fields={
                "title": title,
                "description": description,
                "due_at": due_at,
                "status": status,
                "priority": priority,
                "details": details or {},
            },
        )

    def list_matter_tasks(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        return self._v1_list_related(kind="task", user_id=user_id, matter_id=matter_id)

    def create_matter_note(
        self,
        *,
        user_id: str,
        matter_id: str,
        content: str,
        title: str = "",
        is_private: bool = False,
    ) -> dict[str, Any]:
        return self._v1_create_related(
            kind="note",
            user_id=user_id,
            matter_id=matter_id,
            fields={"title": title, "content": content, "is_private": is_private},
        )

    def list_matter_notes(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        return self._v1_list_related(kind="note", user_id=user_id, matter_id=matter_id)

    def create_matter_event(
        self,
        *,
        user_id: str,
        matter_id: str,
        event_type: str,
        title: str,
        description: str = "",
        event_at: datetime | str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._v1_create_related(
            kind="event",
            user_id=user_id,
            matter_id=matter_id,
            fields={
                "event_type": event_type,
                "title": title,
                "description": description,
                "event_at": event_at or self._now(),
                "source_type": source_type,
                "source_id": source_id,
                "details": details or {},
            },
        )

    def list_matter_events(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        return self._v1_list_related(kind="event", user_id=user_id, matter_id=matter_id)

    def create_matter_document(
        self,
        *,
        user_id: str,
        matter_id: str,
        title: str,
        file_name: str | None = None,
        storage_path: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        sha256: str | None = None,
        extraction_status: str = "pending",
        extracted_text: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._v1_create_related(
            kind="document",
            user_id=user_id,
            matter_id=matter_id,
            fields={
                "title": title,
                "file_name": file_name,
                "storage_path": storage_path,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "extraction_status": extraction_status,
                "extracted_text": extracted_text,
                "details": details or {},
            },
        )

    def list_matter_documents(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        return self._v1_list_related(kind="document", user_id=user_id, matter_id=matter_id)

    def create_matter_research(
        self,
        *,
        user_id: str,
        matter_id: str,
        title: str,
        query: str,
        content: str,
        evidence: list[dict[str, Any]] | None = None,
        verification_status: str = "pending",
    ) -> dict[str, Any]:
        return self._v1_create_related(
            kind="research",
            user_id=user_id,
            matter_id=matter_id,
            fields={
                "title": title,
                "query": query,
                "content": content,
                "evidence": evidence or [],
                "verification_status": verification_status,
            },
        )

    def list_matter_research(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        return self._v1_list_related(kind="research", user_id=user_id, matter_id=matter_id)

    def create_matter_draft(
        self,
        *,
        user_id: str,
        matter_id: str,
        title: str,
        document_type: str,
        status: str = "draft",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id)
        draft_id = str(uuid4())
        if self._backend != "postgres":
            now = self._now()
            row = {
                "draft_id": draft_id,
                "user_id": user_id,
                "matter_id": matter_id,
                "title": title,
                "document_type": document_type,
                "status": status,
                "details": details or {},
                "is_archived": False,
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self._memory_v1_tables["matter_drafts"][draft_id] = row
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO matter_drafts (
                        draft_id, user_id, matter_id, title, document_type, status, details
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        draft_id,
                        user_id,
                        matter_id,
                        title,
                        document_type,
                        status,
                        Jsonb(details or {}),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_row(row)

    def list_matter_drafts(self, user_id: str, matter_id: str) -> list[dict[str, Any]]:
        self._v1_assert_matter_owned(user_id, matter_id)
        if self._backend != "postgres":
            rows = [
                row
                for row in self._memory_v1_tables["matter_drafts"].values()
                if row["user_id"] == user_id
                and row["matter_id"] == matter_id
                and not row["is_archived"]
            ]
            rows.sort(key=lambda item: item["updated_at"], reverse=True)
            return [_serialize_row(row) for row in rows]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM matter_drafts
                    WHERE user_id = %s AND matter_id = %s AND is_archived = FALSE
                    ORDER BY updated_at DESC
                    """,
                    (user_id, matter_id),
                )
                rows = cur.fetchall()
        return [_serialize_row(row) for row in rows]

    def create_draft_version(
        self,
        *,
        user_id: str,
        matter_id: str,
        draft_id: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id)
        version_id = str(uuid4())
        if self._backend != "postgres":
            draft = self._memory_v1_tables["matter_drafts"].get(draft_id)
            if (
                not draft
                or draft["user_id"] != user_id
                or draft["matter_id"] != matter_id
                or draft["is_archived"]
            ):
                raise ValueError("Draft not found.")
            existing = [
                row
                for row in self._memory_v1_tables["draft_versions"].values()
                if row["user_id"] == user_id
                and row["matter_id"] == matter_id
                and row["draft_id"] == draft_id
            ]
            now = self._now()
            row = {
                "version_id": version_id,
                "user_id": user_id,
                "matter_id": matter_id,
                "draft_id": draft_id,
                "version_number": len(existing) + 1,
                "content": content,
                "citations": citations or [],
                "created_by": user_id,
                "is_archived": False,
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self._memory_v1_tables["draft_versions"][version_id] = row
            draft["updated_at"] = now
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT draft_id
                    FROM matter_drafts
                    WHERE user_id = %s
                      AND matter_id = %s
                      AND draft_id = %s
                      AND is_archived = FALSE
                    FOR UPDATE
                    """,
                    (user_id, matter_id, draft_id),
                )
                if not cur.fetchone():
                    raise ValueError("Draft not found.")
                cur.execute(
                    """
                    SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version
                    FROM draft_versions
                    WHERE user_id = %s AND matter_id = %s AND draft_id = %s
                    """,
                    (user_id, matter_id, draft_id),
                )
                version_number = int(cur.fetchone()["next_version"])
                cur.execute(
                    """
                    INSERT INTO draft_versions (
                        version_id, user_id, matter_id, draft_id, version_number,
                        content, citations, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        version_id,
                        user_id,
                        matter_id,
                        draft_id,
                        version_number,
                        content,
                        Jsonb(citations or []),
                        user_id,
                    ),
                )
                row = cur.fetchone()
                cur.execute(
                    """
                    UPDATE matter_drafts
                    SET updated_at = NOW()
                    WHERE user_id = %s AND matter_id = %s AND draft_id = %s
                    """,
                    (user_id, matter_id, draft_id),
                )
            conn.commit()
        return _serialize_row(row)

    def list_draft_versions(
        self,
        user_id: str,
        matter_id: str,
        draft_id: str,
    ) -> list[dict[str, Any]]:
        self._v1_assert_matter_owned(user_id, matter_id, include_archived=True)
        if self._backend != "postgres":
            draft = self._memory_v1_tables["matter_drafts"].get(draft_id)
            if not draft or draft["user_id"] != user_id or draft["matter_id"] != matter_id:
                raise ValueError("Draft not found.")
            rows = [
                row
                for row in self._memory_v1_tables["draft_versions"].values()
                if row["user_id"] == user_id
                and row["matter_id"] == matter_id
                and row["draft_id"] == draft_id
            ]
            rows.sort(key=lambda item: item["version_number"])
            return [_serialize_row(row) for row in rows]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT version.*
                    FROM draft_versions version
                    JOIN matter_drafts draft
                      ON draft.user_id = version.user_id
                     AND draft.matter_id = version.matter_id
                     AND draft.draft_id = version.draft_id
                    WHERE version.user_id = %s
                      AND version.matter_id = %s
                      AND version.draft_id = %s
                    ORDER BY version.version_number
                    """,
                    (user_id, matter_id, draft_id),
                )
                rows = cur.fetchall()
        if not rows:
            draft = [
                row
                for row in self.list_matter_drafts(user_id, matter_id)
                if row["draft_id"] == draft_id
            ]
            if not draft:
                raise ValueError("Draft not found.")
        return [_serialize_row(row) for row in rows]

    def create_agent_run(
        self,
        *,
        user_id: str,
        matter_id: str,
        command: str,
        input_text: str = "",
        status: str = "created",
        context_snapshot: dict[str, Any] | None = None,
        model_id: str | None = None,
        prompt_version: str | None = None,
    ) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id)
        agent_run_id = str(uuid4())
        fields = {
            "agent_run_id": agent_run_id,
            "user_id": user_id,
            "matter_id": matter_id,
            "command": command,
            "input_text": input_text,
            "status": status,
            "context_snapshot": context_snapshot or {},
            "output_text": None,
            "error_text": None,
            "model_id": model_id,
            "prompt_version": prompt_version,
            "token_count": 0,
            "started_at": self._now(),
            "completed_at": None,
            "is_archived": False,
            "archived_at": None,
        }
        if self._backend != "postgres":
            now = self._now()
            row = {**fields, "created_at": now, "updated_at": now}
            self._memory_v1_tables["agent_runs"][agent_run_id] = row
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_runs (
                        agent_run_id, user_id, matter_id, command, input_text,
                        status, context_snapshot, model_id, prompt_version
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        agent_run_id,
                        user_id,
                        matter_id,
                        command,
                        input_text,
                        status,
                        Jsonb(context_snapshot or {}),
                        model_id,
                        prompt_version,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_row(row)

    def update_agent_run(
        self,
        *,
        user_id: str,
        matter_id: str,
        agent_run_id: str,
        status: str,
        output_text: str | None = None,
        error_text: str | None = None,
        token_count: int | None = None,
        completed_at: datetime | None = None,
    ) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id)
        if self._backend != "postgres":
            row = self._memory_v1_tables["agent_runs"].get(agent_run_id)
            if not row or row["user_id"] != user_id or row["matter_id"] != matter_id:
                raise ValueError("Agent run not found.")
            row.update(
                {
                    "status": status,
                    "output_text": output_text,
                    "error_text": error_text,
                    "token_count": token_count if token_count is not None else row["token_count"],
                    "completed_at": completed_at,
                    "updated_at": self._now(),
                }
            )
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_runs
                    SET status = %s,
                        output_text = %s,
                        error_text = %s,
                        token_count = COALESCE(%s, token_count),
                        completed_at = %s
                    WHERE user_id = %s AND matter_id = %s AND agent_run_id = %s
                    RETURNING *
                    """,
                    (
                        status,
                        output_text,
                        error_text,
                        token_count,
                        completed_at,
                        user_id,
                        matter_id,
                        agent_run_id,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        if not row:
            raise ValueError("Agent run not found.")
        return _serialize_row(row)

    def get_agent_run(
        self,
        user_id: str,
        matter_id: str,
        agent_run_id: str,
    ) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id, include_archived=True)
        if self._backend != "postgres":
            row = self._memory_v1_tables["agent_runs"].get(agent_run_id)
            if not row or row["user_id"] != user_id or row["matter_id"] != matter_id:
                raise ValueError("Agent run not found.")
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM agent_runs
                    WHERE user_id = %s AND matter_id = %s AND agent_run_id = %s
                    """,
                    (user_id, matter_id, agent_run_id),
                )
                row = cur.fetchone()
        if not row:
            raise ValueError("Agent run not found.")
        return _serialize_row(row)

    def create_agent_tool_call(
        self,
        *,
        user_id: str,
        matter_id: str,
        agent_run_id: str,
        tool_name: str,
        input_payload: dict[str, Any] | None = None,
        status: str = "started",
    ) -> dict[str, Any]:
        self.get_agent_run(user_id, matter_id, agent_run_id)
        tool_call_id = str(uuid4())
        if self._backend != "postgres":
            now = self._now()
            row = {
                "tool_call_id": tool_call_id,
                "user_id": user_id,
                "matter_id": matter_id,
                "agent_run_id": agent_run_id,
                "tool_name": tool_name,
                "status": status,
                "input_payload": input_payload or {},
                "output_payload": None,
                "error_text": None,
                "started_at": now,
                "completed_at": None,
                "is_archived": False,
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self._memory_v1_tables["agent_tool_calls"][tool_call_id] = row
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_tool_calls (
                        tool_call_id, user_id, matter_id, agent_run_id,
                        tool_name, status, input_payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        tool_call_id,
                        user_id,
                        matter_id,
                        agent_run_id,
                        tool_name,
                        status,
                        Jsonb(input_payload or {}),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_row(row)

    def complete_agent_tool_call(
        self,
        *,
        user_id: str,
        matter_id: str,
        tool_call_id: str,
        status: str,
        output_payload: dict[str, Any] | None = None,
        error_text: str | None = None,
    ) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id, include_archived=True)
        if self._backend != "postgres":
            row = self._memory_v1_tables["agent_tool_calls"].get(tool_call_id)
            if not row or row["user_id"] != user_id or row["matter_id"] != matter_id:
                raise ValueError("Agent tool call not found.")
            row.update(
                {
                    "status": status,
                    "output_payload": output_payload,
                    "error_text": error_text,
                    "completed_at": self._now(),
                    "updated_at": self._now(),
                }
            )
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_tool_calls
                    SET status = %s,
                        output_payload = %s,
                        error_text = %s,
                        completed_at = NOW()
                    WHERE user_id = %s AND matter_id = %s AND tool_call_id = %s
                    RETURNING *
                    """,
                    (
                        status,
                        Jsonb(output_payload) if output_payload is not None else None,
                        error_text,
                        user_id,
                        matter_id,
                        tool_call_id,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        if not row:
            raise ValueError("Agent tool call not found.")
        return _serialize_row(row)

    def list_agent_tool_calls(
        self,
        user_id: str,
        matter_id: str,
        agent_run_id: str,
    ) -> list[dict[str, Any]]:
        self.get_agent_run(user_id, matter_id, agent_run_id)
        if self._backend != "postgres":
            rows = [
                row
                for row in self._memory_v1_tables["agent_tool_calls"].values()
                if row["user_id"] == user_id
                and row["matter_id"] == matter_id
                and row["agent_run_id"] == agent_run_id
                and not row["is_archived"]
            ]
            rows.sort(key=lambda item: item["created_at"])
            return [_serialize_row(row) for row in rows]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM agent_tool_calls
                    WHERE user_id = %s
                      AND matter_id = %s
                      AND agent_run_id = %s
                      AND is_archived = FALSE
                    ORDER BY created_at
                    """,
                    (user_id, matter_id, agent_run_id),
                )
                rows = cur.fetchall()
        return [_serialize_row(row) for row in rows]

    def create_agent_feedback(
        self,
        *,
        user_id: str,
        matter_id: str,
        feedback_type: str,
        rating: int | None = None,
        comment: str = "",
        agent_run_id: str | None = None,
        research_id: str | None = None,
        draft_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._v1_assert_matter_owned(user_id, matter_id)
        if rating is not None and not 1 <= rating <= 5:
            raise ValueError("Feedback rating must be between 1 and 5.")
        if agent_run_id:
            self.get_agent_run(user_id, matter_id, agent_run_id)
        self._v1_assert_optional_owned_record(
            "matter_research", "research_id", research_id, user_id, matter_id
        )
        self._v1_assert_optional_owned_record(
            "matter_drafts", "draft_id", draft_id, user_id, matter_id
        )
        feedback_id = str(uuid4())
        if self._backend != "postgres":
            now = self._now()
            row = {
                "feedback_id": feedback_id,
                "user_id": user_id,
                "matter_id": matter_id,
                "agent_run_id": agent_run_id,
                "research_id": research_id,
                "draft_id": draft_id,
                "feedback_type": feedback_type,
                "rating": rating,
                "comment": comment,
                "details": details or {},
                "is_archived": False,
                "archived_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self._memory_v1_tables["agent_feedback"][feedback_id] = row
            return _serialize_row(row)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_feedback (
                        feedback_id, user_id, matter_id, agent_run_id,
                        research_id, draft_id, feedback_type, rating, comment, details
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        feedback_id,
                        user_id,
                        matter_id,
                        agent_run_id,
                        research_id,
                        draft_id,
                        feedback_type,
                        rating,
                        comment,
                        Jsonb(details or {}),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_row(row)

    def _v1_assert_optional_owned_record(
        self,
        table: str,
        id_field: str,
        record_id: str | None,
        user_id: str,
        matter_id: str,
    ) -> None:
        if not record_id:
            return
        if self._backend != "postgres":
            row = self._memory_v1_tables[table].get(record_id)
            if not row or row["user_id"] != user_id or row["matter_id"] != matter_id:
                raise ValueError("Referenced V1 record not found.")
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT 1
                    FROM {table}
                    WHERE {id_field} = %s AND user_id = %s AND matter_id = %s
                    """,
                    (record_id, user_id, matter_id),
                )
                row = cur.fetchone()
        if not row:
            raise ValueError("Referenced V1 record not found.")

    def list_agent_feedback(
        self,
        user_id: str,
        matter_id: str,
    ) -> list[dict[str, Any]]:
        self._v1_assert_matter_owned(user_id, matter_id, include_archived=True)
        if self._backend != "postgres":
            rows = [
                row
                for row in self._memory_v1_tables["agent_feedback"].values()
                if row["user_id"] == user_id
                and row["matter_id"] == matter_id
                and not row["is_archived"]
            ]
            rows.sort(key=lambda item: item["created_at"], reverse=True)
            return [_serialize_row(row) for row in rows]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM agent_feedback
                    WHERE user_id = %s AND matter_id = %s AND is_archived = FALSE
                    ORDER BY created_at DESC
                    """,
                    (user_id, matter_id),
                )
                rows = cur.fetchall()
        return [_serialize_row(row) for row in rows]
