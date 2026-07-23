"""Offline indexing and request-time retrieval for the large JSON legal corpus."""

from __future__ import annotations

from collections import Counter
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Callable, Iterator

import ijson
from ijson.common import JSONError


SCHEMA_VERSION = "2"
COLLECTIONS = {
    "json_judgements": "case",
    "json_judgements_files": "case",
    "json_law_files": "statute",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "i", "in", "is", "it", "its",
    "may", "not", "of", "on", "or", "shall", "she", "that", "the", "their",
    "this", "to", "was", "were", "what", "when", "where", "which", "who",
    "will", "with", "would", "you", "your",
}


@dataclass(frozen=True)
class CorpusSearchHit:
    authority_type: str
    title: str
    year: str
    court: str
    page_number: str
    section: str
    chunk_id: str
    chunk_text: str
    source_path: str
    source_json: str
    score: float


@dataclass(frozen=True)
class IndexBuildStats:
    files_seen: int
    records_seen: int
    records_indexed: int
    records_skipped: int
    duplicate_records: int


def tokenize_for_index(value: object) -> list[str]:
    tokens: list[str] = []
    for token in _TOKEN_PATTERN.findall(str(value or "").lower()):
        if token in _STOP_WORDS or len(token) < 2:
            continue
        tokens.append(token)
        if token.endswith("ies") and len(token) > 4:
            tokens.append(f"{token[:-3]}y")
        elif token.endswith("s") and len(token) > 4:
            tokens.append(token[:-1])
    return tokens


def _flatten(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _weighted_terms(record: dict[str, object]) -> Counter[str]:
    weighted: Counter[str] = Counter()
    fields = (
        (record.get("chunk_text"), 1.0),
        (record.get("title"), 4.0),
        (record.get("court"), 3.0),
        (record.get("year"), 2.0),
        (record.get("section"), 3.0),
        (record.get("citations"), 2.5),
        (record.get("precedents"), 2.5),
        (record.get("statutes"), 3.0),
        (record.get("legal_issues"), 2.0),
        (record.get("holding"), 2.5),
        (record.get("petition_numbers"), 2.0),
        (record.get("entities"), 2.0),
    )
    for value, weight in fields:
        for token in tokenize_for_index(_flatten(value)):
            weighted[token] += weight
    return weighted


def _iter_json_records(path: Path) -> Iterator[object]:
    with path.open("rb") as handle:
        yield from ijson.items(handle, "item")


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            chunk_id TEXT NOT NULL UNIQUE,
            collection TEXT NOT NULL,
            authority_type TEXT NOT NULL CHECK(authority_type IN ('statute', 'case')),
            document_id TEXT NOT NULL,
            title TEXT NOT NULL,
            year TEXT NOT NULL,
            court TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_json TEXT NOT NULL,
            page_number TEXT NOT NULL,
            section_name TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            document_length REAL NOT NULL
        );
        CREATE TABLE postings (
            document_id INTEGER NOT NULL,
            authority_type TEXT NOT NULL CHECK(authority_type IN ('statute', 'case')),
            term TEXT NOT NULL,
            weighted_tf REAL NOT NULL,
            PRIMARY KEY (document_id, term),
            FOREIGN KEY(document_id) REFERENCES documents(id)
        ) WITHOUT ROWID;
        CREATE TABLE term_stats (
            term TEXT PRIMARY KEY,
            document_frequency INTEGER NOT NULL
        ) WITHOUT ROWID;
        """
    )


def _compact_metadata(record: dict[str, object]) -> str:
    fields = {
        key: record.get(key)
        for key in (
            "jurisdiction", "domain", "citations", "precedents", "statutes",
            "legal_issues", "holding", "petition_numbers", "entities",
        )
        if record.get(key) not in (None, "", [], {})
    }
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":"), default=str)


def build_corpus_index(
    corpus_root: Path,
    output_path: Path,
    *,
    collections: dict[str, str] | None = None,
    diagnostics: list[str] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> IndexBuildStats:
    """Stream all configured JSON arrays into a new, atomically replaced index."""

    corpus_root = Path(corpus_root).resolve()
    output_path = Path(output_path).resolve()
    selected_collections = collections or COLLECTIONS
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f"{output_path.name}.building")
    if temporary_path.exists():
        temporary_path.unlink()

    messages = diagnostics if diagnostics is not None else []
    files_seen = records_seen = records_indexed = records_skipped = duplicates = 0
    term_document_frequencies: Counter[str] = Counter()
    connection = sqlite3.connect(temporary_path)
    try:
        _create_schema(connection)
        for collection, authority_type in selected_collections.items():
            directory = corpus_root / collection
            if not directory.is_dir():
                messages.append(f"Missing corpus directory: {directory}")
                continue

            for json_path in sorted(directory.glob("*.json")):
                files_seen += 1
                try:
                    records = _iter_json_records(json_path)
                    for raw_record in records:
                        records_seen += 1
                        if not isinstance(raw_record, dict):
                            records_skipped += 1
                            messages.append(f"{json_path}: record {records_seen} is not an object")
                            continue
                        record = raw_record
                        chunk_id = str(record.get("chunk_id") or "").strip()
                        chunk_text = str(record.get("chunk_text") or "").strip()
                        if not chunk_id or not chunk_text:
                            records_skipped += 1
                            messages.append(f"{json_path}: skipped record without chunk_id or chunk_text")
                            continue
                        weighted_terms = _weighted_terms(record)
                        if not weighted_terms:
                            records_skipped += 1
                            messages.append(f"{json_path}: skipped empty searchable record {chunk_id}")
                            continue

                        try:
                            cursor = connection.execute(
                                """
                                INSERT INTO documents (
                                    chunk_id, collection, authority_type, document_id, title, year,
                                    court, source_path, source_json, page_number, section_name,
                                    chunk_text, metadata_json, document_length
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    chunk_id,
                                    collection,
                                    authority_type,
                                    str(record.get("document_id") or "").strip(),
                                    str(record.get("title") or "Untitled legal document").strip(),
                                    str(record.get("year") or "").strip(),
                                    str(record.get("court") or "").strip(),
                                    str(record.get("source_path") or "").strip(),
                                    f"{collection}/{json_path.name}",
                                    str(record.get("page_number") or "").strip(),
                                    str(record.get("section") or "").strip(),
                                    chunk_text,
                                    _compact_metadata(record),
                                    float(sum(weighted_terms.values())),
                                ),
                            )
                        except sqlite3.IntegrityError:
                            duplicates += 1
                            continue

                        document_key = int(cursor.lastrowid)
                        connection.executemany(
                            """
                            INSERT INTO postings(term, document_id, authority_type, weighted_tf)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                (term, document_key, authority_type, frequency)
                                for term, frequency in weighted_terms.items()
                            ),
                        )
                        term_document_frequencies.update(weighted_terms.keys())
                        records_indexed += 1
                        if records_indexed % 2000 == 0:
                            connection.commit()
                        if progress is not None and records_indexed % 1000 == 0:
                            progress(files_seen, records_indexed)
                except (OSError, ValueError, JSONError) as exc:
                    records_skipped += 1
                    messages.append(f"Could not parse {json_path}: {exc}")

        if records_indexed == 0:
            raise ValueError("No valid corpus records were indexed")

        average_length = connection.execute(
            "SELECT AVG(document_length) FROM documents"
        ).fetchone()[0]
        connection.executemany(
            "INSERT INTO term_stats(term, document_frequency) VALUES (?, ?)",
            term_document_frequencies.items(),
        )
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "document_count": str(records_indexed),
            "average_document_length": str(float(average_length or 1.0)),
            "corpus_root": str(corpus_root),
        }
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items()
        )
        connection.execute(
            "CREATE INDEX postings_search_idx "
            "ON postings(authority_type, term, document_id, weighted_tf)"
        )
        connection.commit()
        connection.execute("PRAGMA optimize")
    except Exception:
        connection.close()
        if temporary_path.exists():
            temporary_path.unlink()
        raise
    else:
        connection.close()
        temporary_path.replace(output_path)

    return IndexBuildStats(
        files_seen=files_seen,
        records_seen=records_seen,
        records_indexed=records_indexed,
        records_skipped=records_skipped,
        duplicate_records=duplicates,
    )


class LegalCorpusIndex:
    """Read-only BM25-style search over a generated corpus index."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def is_compatible(self) -> bool:
        if not self.path.is_file():
            return False
        try:
            with closing(sqlite3.connect(f"file:{self.path.resolve()}?mode=ro", uri=True)) as connection:
                row = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'schema_version'"
                ).fetchone()
                return bool(row and row[0] == SCHEMA_VERSION)
        except sqlite3.Error:
            return False

    def search(self, query: str, authority_type: str, *, limit: int, candidate_limit: int) -> list[CorpusSearchHit]:
        if limit <= 0 or authority_type not in {"statute", "case"}:
            return []
        query_terms = sorted(set(tokenize_for_index(query)))
        if not query_terms:
            return []

        uri = f"file:{self.path.resolve()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            if metadata.get("schema_version") != SCHEMA_VERSION:
                raise sqlite3.DatabaseError("Incompatible legal corpus index schema")
            document_count = max(1, int(metadata["document_count"]))
            average_length = max(1.0, float(metadata["average_document_length"]))
            placeholders = ",".join("?" for _ in query_terms)
            stats = dict(
                connection.execute(
                    f"SELECT term, document_frequency FROM term_stats WHERE term IN ({placeholders})",
                    query_terms,
                )
            )
            ranked_terms = sorted(
                (term for term in query_terms if term in stats),
                key=lambda term: (stats[term], term),
            )[:4]
            informative = [term for term in ranked_terms if stats[term] / document_count <= 0.35]
            if informative:
                ranked_terms = informative
            elif any(stats[term] / document_count > 0.35 for term in ranked_terms):
                return []
            if not ranked_terms:
                return []

            term_placeholders = ",".join("?" for _ in ranked_terms)
            rows = connection.execute(
                f"""
                SELECT term, document_id, weighted_tf
                FROM postings p
                WHERE authority_type = ? AND term IN ({term_placeholders})
                """,
                (authority_type, *ranked_terms),
            )
            scores: dict[int, float] = {}
            frequencies: dict[int, dict[str, float]] = {}
            k1, b = 1.5, 0.75
            for term, document_id, term_frequency in rows:
                document_frequency = int(stats[term])
                inverse_frequency = math.log(
                    1.0 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = term_frequency + k1
                contribution = inverse_frequency * (term_frequency * (k1 + 1.0)) / denominator
                scores[int(document_id)] = scores.get(int(document_id), 0.0) + contribution
                frequencies.setdefault(int(document_id), {})[str(term)] = float(term_frequency)

            candidate_ids = [
                key for key, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:candidate_limit]
            ]
            if not candidate_ids:
                return []
            candidate_placeholders = ",".join("?" for _ in candidate_ids)
            documents = {
                int(row[0]): row[1:]
                for row in connection.execute(
                    f"""
                    SELECT id, title, year, court, page_number, section_name, chunk_id,
                           chunk_text, source_path, source_json, document_length
                    FROM documents WHERE id IN ({candidate_placeholders})
                    """,
                    candidate_ids,
                )
            }

        query_text = query.lower()
        section_terms = set(re.findall(r"\b(?:section\s*)?(\d+[a-z]?(?:\(\d+\))?)\b", query_text))
        hits: list[CorpusSearchHit] = []
        for document_id in candidate_ids:
            title, year, court, page, section, chunk_id, text, source_path, source_json, document_length = documents[document_id]
            score = 0.0
            for term, term_frequency in frequencies[document_id].items():
                document_frequency = int(stats[term])
                inverse_frequency = math.log(
                    1.0 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = term_frequency + k1 * (
                    1.0 - b + b * float(document_length) / average_length
                )
                score += inverse_frequency * (term_frequency * (k1 + 1.0)) / denominator
            searchable = f"{title} {section} {text}".lower()
            if authority_type == "case" and "supreme court" in str(court).lower():
                score += 1.5
            if section_terms and any(
                re.search(rf"\b(?:section\s*)?{re.escape(term)}\b", searchable)
                for term in section_terms
            ):
                score += 5.0
            if title and str(title).lower() in query_text:
                score += 6.0
            hits.append(
                CorpusSearchHit(
                    authority_type=authority_type,
                    title=str(title), year=str(year), court=str(court), page_number=str(page),
                    section=str(section), chunk_id=str(chunk_id), chunk_text=str(text),
                    source_path=str(source_path), source_json=str(source_json), score=round(score, 6),
                )
            )
        hits.sort(key=lambda item: (-item.score, item.title.lower(), item.chunk_id))
        return hits[:limit]
