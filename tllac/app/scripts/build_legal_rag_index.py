"""Build the offline search index for the large JSON legal corpus."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from app.services.legal_corpus_index import build_corpus_index


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / "tllac" / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path(os.getenv("LEGAL_RAG_CORPUS_ROOT", str(REPO_ROOT))),
        help="Directory containing json_judgements, json_judgements_files, and json_law_files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            os.getenv(
                "LEGAL_RAG_INDEX_PATH",
                str(REPO_ROOT / "tllac" / "app" / "data" / "legal_corpus.sqlite3"),
            )
        ),
        help="Destination SQLite index path",
    )
    args = parser.parse_args()
    diagnostics: list[str] = []
    stats = build_corpus_index(
        args.corpus_root,
        args.output,
        diagnostics=diagnostics,
        progress=lambda files, records: print(
            f"Indexed {records} records from {files} files...", flush=True
        ),
    )
    for message in diagnostics:
        print(f"warning: {message}")
    print(
        f"Built {args.output}: {stats.records_indexed} records from {stats.files_seen} files; "
        f"{stats.records_skipped} skipped, {stats.duplicate_records} duplicates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
