from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from pypdf import PdfReader

from ..db.db_client import db_client

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / "tllac" / ".env")

_DEFAULT_UPLOAD_ROOT = _REPO_ROOT / "tllac" / "uploads"
_ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}
_WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _backend() -> str:
    return str(getattr(db_client, "_backend", "postgres"))


def _memory_documents() -> dict[str, dict[str, Any]]:
    return getattr(db_client, "_memory_documents")


def _memory_chunks() -> dict[str, list[dict[str, Any]]]:
    return getattr(db_client, "_memory_document_chunks")


def _configured_upload_root() -> Path:
    configured = os.getenv("MATTER_DOCUMENT_UPLOAD_ROOT", "").strip()
    if not configured:
        return _DEFAULT_UPLOAD_ROOT
    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = _REPO_ROOT / root
    return root


def get_upload_root() -> Path:
    root = _configured_upload_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _safe_path_component(value: str) -> str:
    component = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip()).strip("._-")
    return component or "item"


def _sanitize_filename(filename: str) -> str:
    safe_name = Path(filename or "").name.strip()
    if not safe_name:
        raise ValueError("A filename is required.")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(safe_name).stem).strip("._-")
    suffix = re.sub(r"[^A-Za-z0-9.]+", "", Path(safe_name).suffix.lower())
    if not stem:
        stem = "document"
    if len(stem) > 80:
        stem = stem[:80]
    return f"{stem}{suffix}"


def _split_paragraphs(text: str) -> list[str]:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    parts = [part.strip() for part in re.split(r"\n\s*\n+", normalized) if part.strip()]
    if len(parts) == 1 and "\n" in normalized:
        line_parts = [line.strip() for line in normalized.split("\n") if line.strip()]
        if len(line_parts) > 1:
            parts = line_parts
    return [_normalize_whitespace(part) for part in parts if _normalize_whitespace(part)]


def _split_text_into_chunks(text: str, *, max_chars: int = 1200, overlap_chars: int = 150) -> list[str]:
    words = _normalize_whitespace(text).split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []

    def current_length(words_list: list[str]) -> int:
        return len(" ".join(words_list))

    for word in words:
        candidate = current + [word]
        if current and current_length(candidate) > max_chars:
            chunks.append(" ".join(current).strip())
            if overlap_chars > 0 and current:
                overlap: list[str] = []
                for item in reversed(current):
                    tentative = [item, *overlap]
                    if overlap and current_length(tentative) > overlap_chars:
                        break
                    overlap = tentative
                current = overlap[:] if overlap else []
            else:
                current = []
            candidate = current + [word]
        current.append(word)

    if current:
        chunks.append(" ".join(current).strip())

    return [chunk for chunk in chunks if chunk]


def _extract_docx_paragraphs(path: Path) -> list[str]:
    if not zipfile.is_zipfile(path):
        raise ValueError("DOCX files must be valid Office Open XML archives.")

    with zipfile.ZipFile(path) as archive:
        if "word/document.xml" not in archive.namelist():
            raise ValueError("DOCX file is missing document content.")
        with archive.open("word/document.xml") as handle:
            root = ET.parse(handle).getroot()

    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", _WORD_NAMESPACE):
        pieces = [node.text or "" for node in paragraph.findall(".//w:t", _WORD_NAMESPACE)]
        text = _normalize_whitespace("".join(pieces))
        if text:
            paragraphs.append(text)
    return paragraphs


def _extract_pdf_units(path: Path) -> list[dict[str, Any]]:
    reader = PdfReader(str(path))
    units: list[dict[str, Any]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        for paragraph_number, paragraph_text in enumerate(_split_paragraphs(page_text), start=1):
            units.append(
                {
                    "page_number": page_number,
                    "paragraph_number": paragraph_number,
                    "text": paragraph_text,
                }
            )
    return units


def _extract_docx_units(path: Path) -> list[dict[str, Any]]:
    return [
        {"page_number": None, "paragraph_number": index, "text": paragraph}
        for index, paragraph in enumerate(_extract_docx_paragraphs(path), start=1)
    ]


def _extract_txt_units(path: Path) -> list[dict[str, Any]]:
    try:
        raw_text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("TXT files must be UTF-8 encoded.") from exc
    return [
        {"page_number": None, "paragraph_number": index, "text": paragraph}
        for index, paragraph in enumerate(_split_paragraphs(raw_text), start=1)
    ]


def extract_document_units(path: Path, file_extension: str) -> list[dict[str, Any]]:
    extension = file_extension.lower()
    if extension == ".pdf":
        return _extract_pdf_units(path)
    if extension == ".docx":
        return _extract_docx_units(path)
    if extension == ".txt":
        return _extract_txt_units(path)
    raise ValueError("Unsupported document type.")


def build_chunk_rows(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunk_rows: list[dict[str, Any]] = []
    chunk_position = 1
    for unit in units:
        for chunk_text in _split_text_into_chunks(str(unit.get("text") or "")):
            chunk_rows.append(
                {
                    "page_number": unit.get("page_number"),
                    "paragraph_number": unit.get("paragraph_number"),
                    "chunk_position": chunk_position,
                    "chunk_text": chunk_text,
                }
            )
            chunk_position += 1
    return chunk_rows


def _write_file(source: Any, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as target:
        shutil.copyfileobj(source, target)


def _resolve_storage_path(user_id: str, matter_id: str, original_filename: str, document_id: str) -> Path:
    user_folder = get_upload_root() / f"user_{_safe_path_component(user_id)}"
    matter_folder = user_folder / f"matter_{_safe_path_component(matter_id)}"
    matter_folder.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(original_filename)
    candidate = matter_folder / safe_name
    if candidate.exists():
        candidate = matter_folder / f"{Path(safe_name).stem}_{document_id[:8]}{Path(safe_name).suffix}"
    return candidate


def _validate_upload_extension(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, DOCX, and TXT files are supported.")
    return suffix


def _validate_file_signature(path: Path, file_extension: str) -> None:
    if file_extension == ".pdf":
        with path.open("rb") as handle:
            header = handle.read(5)
        if header != b"%PDF-":
            raise ValueError("Uploaded PDF file is not a valid PDF document.")
        return

    if file_extension == ".docx" and not zipfile.is_zipfile(path):
        raise ValueError("Uploaded DOCX file is not a valid Office document.")


def _store_document_record(
    *,
    document_id: str,
    user_id: str,
    matter_id: str,
    original_filename: str,
    storage_path: str,
    mime_type: str,
    file_extension: str,
    chunk_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if _backend() != "postgres":
        documents = _memory_documents()
        chunks = _memory_chunks()
        documents[document_id] = {
            "document_id": document_id,
            "user_id": user_id,
            "matter_id": matter_id,
            "original_filename": original_filename,
            "storage_path": storage_path,
            "mime_type": mime_type,
            "file_extension": file_extension,
            "upload_timestamp": _now(),
            "status": "active",
        }
        chunks[document_id] = [
            {
                "chunk_id": str(uuid4()),
                "document_id": document_id,
                "user_id": user_id,
                "matter_id": matter_id,
                "page_number": row.get("page_number"),
                "paragraph_number": row.get("paragraph_number"),
                "chunk_position": int(row["chunk_position"]),
                "chunk_text": str(row["chunk_text"]),
            }
            for row in chunk_rows
        ]
        return get_document_metadata(user_id, document_id)

    with db_client._connect() as conn:  # noqa: SLF001 - reuse existing connection details
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO matter_documents (
                    document_id,
                    user_id,
                    matter_id,
                    original_filename,
                    storage_path,
                    mime_type,
                    file_extension,
                    upload_timestamp,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'active')
                """,
                (
                    document_id,
                    user_id,
                    matter_id,
                    original_filename,
                    storage_path,
                    mime_type,
                    file_extension,
                ),
            )
            if chunk_rows:
                cur.executemany(
                    """
                    INSERT INTO matter_document_chunks (
                        chunk_id,
                        document_id,
                        user_id,
                        matter_id,
                        page_number,
                        paragraph_number,
                        chunk_position,
                        chunk_text
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            str(uuid4()),
                            document_id,
                            user_id,
                            matter_id,
                            row.get("page_number"),
                            row.get("paragraph_number"),
                            int(row["chunk_position"]),
                            str(row["chunk_text"]),
                        )
                        for row in chunk_rows
                    ],
                )
        conn.commit()
    return get_document_metadata(user_id, document_id)


def process_uploaded_document(
    *,
    user_id: str,
    matter_id: str,
    uploaded_file: Any,
) -> dict[str, Any]:
    original_filename = uploaded_file.filename or ""
    file_extension = _validate_upload_extension(original_filename)
    document_id = str(uuid4())
    storage_path = _resolve_storage_path(user_id, matter_id, original_filename, document_id)
    _write_file(uploaded_file.file, storage_path)

    try:
        _validate_file_signature(storage_path, file_extension)
        units = extract_document_units(storage_path, file_extension)
        chunk_rows = build_chunk_rows(units)
        if not chunk_rows:
            raise ValueError("Uploaded document does not contain any extractable text.")
        return _store_document_record(
            document_id=document_id,
            user_id=user_id,
            matter_id=matter_id,
            original_filename=original_filename,
            storage_path=str(storage_path),
            mime_type=uploaded_file.content_type or _ALLOWED_EXTENSIONS[file_extension],
            file_extension=file_extension,
            chunk_rows=chunk_rows,
        )
    except Exception:
        if storage_path.exists():
            storage_path.unlink()
        raise


def _format_document_row(row: dict[str, Any], *, chunk_count: int = 0) -> dict[str, Any]:
    upload_timestamp = row.get("upload_timestamp")
    if hasattr(upload_timestamp, "astimezone"):
        timestamp = upload_timestamp.astimezone(timezone.utc).isoformat()
    else:
        timestamp = str(upload_timestamp) if upload_timestamp is not None else ""
    result = {
        "document_id": str(row.get("document_id", "")),
        "user_id": str(row.get("user_id", "")),
        "matter_id": str(row.get("matter_id", "")),
        "original_filename": str(row.get("original_filename", "")),
        "storage_path": str(row.get("storage_path", "")),
        "mime_type": str(row.get("mime_type", "")),
        "file_extension": str(row.get("file_extension", "")),
        "upload_timestamp": timestamp,
        "status": str(row.get("status", "active")),
        "chunk_count": int(chunk_count),
    }
    return result


def list_documents(user_id: str, matter_id: str) -> list[dict[str, Any]]:
    if _backend() != "postgres":
        documents = [
            row
            for row in _memory_documents().values()
            if row["user_id"] == user_id and row["matter_id"] == matter_id
        ]
        documents.sort(key=lambda item: item["upload_timestamp"], reverse=True)
        return [
            _format_document_row(
                row,
                chunk_count=len(_memory_chunks().get(row["document_id"], [])),
            )
            for row in documents
        ]

    with db_client._connect() as conn:  # noqa: SLF001 - reuse existing connection details
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.document_id, d.user_id, d.matter_id, d.original_filename,
                       d.storage_path, d.mime_type, d.file_extension, d.upload_timestamp,
                       d.status, COUNT(c.chunk_id) AS chunk_count
                FROM matter_documents d
                LEFT JOIN matter_document_chunks c ON c.document_id = d.document_id
                WHERE d.user_id = %s AND d.matter_id = %s
                GROUP BY d.document_id
                ORDER BY d.upload_timestamp DESC
                """,
                (user_id, matter_id),
            )
            rows = cur.fetchall()
    return [_format_document_row(dict(row), chunk_count=row["chunk_count"]) for row in rows]


def get_document_metadata(user_id: str, document_id: str) -> dict[str, Any]:
    if _backend() != "postgres":
        row = _memory_documents().get(document_id)
        if not row or row["user_id"] != user_id:
            raise ValueError("Document not found.")
        return _format_document_row(
            row,
            chunk_count=len(_memory_chunks().get(document_id, [])),
        )

    with db_client._connect() as conn:  # noqa: SLF001 - reuse existing connection details
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT document_id, user_id, matter_id, original_filename, storage_path,
                       mime_type, file_extension, upload_timestamp, status
                FROM matter_documents
                WHERE document_id = %s AND user_id = %s
                """,
                (document_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found.")
            cur.execute(
                """
                SELECT COUNT(*) AS chunk_count
                FROM matter_document_chunks
                WHERE document_id = %s
                """,
                (document_id,),
            )
            chunk_row = cur.fetchone()
    return _format_document_row(dict(row), chunk_count=int(chunk_row["chunk_count"]) if chunk_row else 0)


def update_document_status(user_id: str, document_id: str, status: str) -> dict[str, Any]:
    normalized_status = status.strip().lower()
    if normalized_status not in {"active", "deleted", "archived"}:
        raise ValueError("Invalid document status.")

    if _backend() != "postgres":
        row = _memory_documents().get(document_id)
        if not row or row["user_id"] != user_id:
            raise ValueError("Document not found.")
        row["status"] = normalized_status
        return _format_document_row(
            row,
            chunk_count=len(_memory_chunks().get(document_id, [])),
        )

    with db_client._connect() as conn:  # noqa: SLF001 - reuse existing connection details
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE matter_documents
                SET status = %s
                WHERE document_id = %s AND user_id = %s
                RETURNING document_id, user_id, matter_id, original_filename, storage_path,
                          mime_type, file_extension, upload_timestamp, status
                """,
                (normalized_status, document_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found.")
            cur.execute(
                """
                SELECT COUNT(*) AS chunk_count
                FROM matter_document_chunks
                WHERE document_id = %s
                """,
                (document_id,),
            )
            chunk_row = cur.fetchone()
        conn.commit()
    return _format_document_row(dict(row), chunk_count=int(chunk_row["chunk_count"]) if chunk_row else 0)


def delete_document(user_id: str, document_id: str) -> dict[str, Any]:
    return update_document_status(user_id, document_id, "deleted")


def archive_document(user_id: str, document_id: str) -> dict[str, Any]:
    return update_document_status(user_id, document_id, "archived")


def get_document_file_path(user_id: str, document_id: str) -> Path:
    metadata = get_document_metadata(user_id, document_id)
    storage_path = Path(metadata["storage_path"])
    if metadata["status"] == "deleted":
        raise ValueError("Document not found.")
    if not storage_path.is_file():
        raise ValueError("Document file is unavailable.")
    return storage_path


def _search_tokens(query: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9]+", (query or "").lower()):
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def search_documents(
    user_id: str,
    matter_id: str,
    query: str,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    normalized_query = _normalize_whitespace(query)
    if not normalized_query or limit <= 0:
        return []

    if _backend() != "postgres":
        query_tokens = _search_tokens(normalized_query)
        if not query_tokens:
            return []
        scored_results: list[tuple[float, dict[str, Any]]] = []
        for document_id, document in _memory_documents().items():
            if document["user_id"] != user_id or document["matter_id"] != matter_id:
                continue
            if document["status"] != "active":
                continue
            for chunk in _memory_chunks().get(document_id, []):
                chunk_tokens = set(_search_tokens(chunk["chunk_text"]))
                overlap = len(set(query_tokens) & chunk_tokens)
                if not overlap:
                    continue
                scored_results.append(
                    (
                        float(overlap),
                        {
                            "chunk_text": chunk["chunk_text"],
                            "document_id": document_id,
                            "document_name": document["original_filename"],
                            "page_number": chunk["page_number"],
                            "paragraph_number": chunk["paragraph_number"],
                            "chunk_position": int(chunk["chunk_position"]),
                        },
                    )
                )
        scored_results.sort(
            key=lambda item: (
                -item[0],
                item[1]["document_name"].lower(),
                item[1]["chunk_position"],
            )
        )
        return [item[1] for item in scored_results[:limit]]

    with db_client._connect() as conn:  # noqa: SLF001 - reuse existing connection details
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.chunk_text,
                    c.document_id,
                    d.original_filename,
                    c.page_number,
                    c.paragraph_number,
                    c.chunk_position,
                    ts_rank_cd(
                        to_tsvector('simple', c.chunk_text),
                        plainto_tsquery('simple', %s)
                    ) AS score
                FROM matter_document_chunks c
                JOIN matter_documents d ON d.document_id = c.document_id
                WHERE d.user_id = %s
                  AND d.matter_id = %s
                  AND d.status = 'active'
                  AND to_tsvector('simple', c.chunk_text) @@ plainto_tsquery('simple', %s)
                ORDER BY score DESC, d.upload_timestamp DESC, c.chunk_position ASC
                LIMIT %s
                """,
                (normalized_query, user_id, matter_id, normalized_query, limit),
            )
            rows = cur.fetchall()
            if rows:
                return [
                    {
                        "chunk_text": row["chunk_text"],
                        "document_id": str(row["document_id"]),
                        "document_name": row["original_filename"],
                        "page_number": row["page_number"],
                        "paragraph_number": row["paragraph_number"],
                        "chunk_position": int(row["chunk_position"]),
                    }
                    for row in rows
                ]

            query_tokens = _search_tokens(normalized_query)
            if not query_tokens:
                return []
            like_clauses = " OR ".join("LOWER(c.chunk_text) LIKE %s" for _ in query_tokens[:6])
            like_params = [f"%{token}%" for token in query_tokens[:6]]
            cur.execute(
                f"""
                SELECT
                    c.chunk_text,
                    c.document_id,
                    d.original_filename,
                    c.page_number,
                    c.paragraph_number,
                    c.chunk_position
                FROM matter_document_chunks c
                JOIN matter_documents d ON d.document_id = c.document_id
                WHERE d.user_id = %s
                  AND d.matter_id = %s
                  AND d.status = 'active'
                  AND ({like_clauses})
                ORDER BY d.upload_timestamp DESC, c.chunk_position ASC
                LIMIT %s
                """,
                (user_id, matter_id, *like_params, limit),
            )
            fallback_rows = cur.fetchall()

    return [
        {
            "chunk_text": row["chunk_text"],
            "document_id": str(row["document_id"]),
            "document_name": row["original_filename"],
            "page_number": row["page_number"],
            "paragraph_number": row["paragraph_number"],
            "chunk_position": int(row["chunk_position"]),
        }
        for row in fallback_rows
    ]


def build_matter_document_context(user_id: str, matter_id: str, query: str, *, limit: int = 4) -> str:
    hits = search_documents(user_id, matter_id, query, limit=limit)
    if not hits:
        return ""

    lines = [
        "Retrieved matter documents:",
        "Answer only from the matter-document excerpts below when using this context.",
        "Do not invent facts that are not present in the excerpts.",
        "",
    ]
    for item in hits:
        location_bits = []
        if item.get("page_number") is not None:
            location_bits.append(f"page {item['page_number']}")
        if item.get("paragraph_number") is not None:
            location_bits.append(f"paragraph {item['paragraph_number']}")
        location_bits.append(f"chunk {item['chunk_position']}")
        location = ", ".join(location_bits)
        snippet = _normalize_whitespace(str(item.get("chunk_text") or ""))
        if len(snippet) > 520:
            snippet = f"{snippet[:517].rstrip()}..."
        lines.append(
            f"- {item['document_name']} ({location}) [document {item['document_id']}]: {snippet}"
        )
    return "\n".join(lines)
