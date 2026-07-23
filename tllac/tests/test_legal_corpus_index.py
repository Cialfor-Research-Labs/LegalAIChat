import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tllac"))

from app.services.legal_corpus_index import LegalCorpusIndex, build_corpus_index
from app.services.legal_rag_service import retrieve_legal_rag_result


def _write_json(path: Path, records: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")


class LegalCorpusIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.index_path = self.root / "legal-corpus.sqlite3"

        _write_json(
            self.root / "json_law_files" / "specific-relief.json",
            [
                {
                    "document_id": "law-1",
                    "document_type": "judgement",
                    "title": "The Specific Relief Act, 1963",
                    "year": 1963,
                    "source_path": "law docs/Specific Relief Act.txt",
                    "chunk_id": "law-1-c1",
                    "chunk_text": "Section 14 explains contracts which cannot be specifically enforced.",
                    "section": "Section 14",
                    "statutes": ["Specific Relief Act"],
                },
                {"chunk_id": "empty-law", "chunk_text": ""},
            ],
        )
        _write_json(
            self.root / "json_judgements" / "constitutional.json",
            [
                {
                    "document_id": "case-1",
                    "title": "Kesavananda Bharati v. State of Kerala",
                    "year": 1973,
                    "court": "Supreme Court of India",
                    "source_path": "judgements/kesavananda.pdf",
                    "page_number": 12,
                    "chunk_id": "case-1-c1",
                    "chunk_text": "The Constitution has a basic structure which Parliament cannot destroy.",
                    "citations": ["AIR 1973 SC 1461"],
                    "legal_issues": ["constitutional amendment and basic structure"],
                },
                "not-an-object",
            ],
        )
        _write_json(
            self.root / "json_judgements_files" / "duplicate.json",
            [
                {
                    "document_id": "duplicate-case",
                    "title": "Duplicate copy",
                    "chunk_id": "case-1-c1",
                    "chunk_text": "This duplicate must not replace the first record.",
                },
                {
                    "document_id": "case-2",
                    "title": "Municipal Council v. Consumer",
                    "year": 2001,
                    "court": "High Court of Delhi",
                    "chunk_id": "case-2-c1",
                    "chunk_text": "A consumer compensation claim concerned deficient municipal services.",
                    "holding": "Deficient public services may justify consumer compensation.",
                },
            ],
        )
        (self.root / "json_judgements_files" / "malformed.json").write_text("[{", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _build(self):
        diagnostics: list[str] = []
        stats = build_corpus_index(self.root, self.index_path, diagnostics=diagnostics)
        return stats, diagnostics

    def test_build_classifies_sources_deduplicates_and_skips_invalid_records(self) -> None:
        stats, diagnostics = self._build()

        self.assertEqual(stats.records_indexed, 3)
        self.assertEqual(stats.duplicate_records, 1)
        self.assertEqual(stats.records_skipped, 3)
        self.assertTrue(any("not an object" in item for item in diagnostics))
        self.assertTrue(any("Could not parse" in item for item in diagnostics))
        self.assertTrue(LegalCorpusIndex(self.index_path).is_compatible())

        statutes = LegalCorpusIndex(self.index_path).search(
            "Specific Relief Act section 14 specifically enforced",
            "statute",
            limit=3,
            candidate_limit=20,
        )
        cases = LegalCorpusIndex(self.index_path).search(
            "Kesavananda Bharati constitutional basic structure AIR 1973",
            "case",
            limit=3,
            candidate_limit=20,
        )

        self.assertEqual(statutes[0].chunk_id, "law-1-c1")
        self.assertEqual(statutes[0].authority_type, "statute")
        self.assertEqual(cases[0].chunk_id, "case-1-c1")
        self.assertEqual(cases[0].court, "Supreme Court of India")

    def test_search_is_stable_and_supports_natural_language(self) -> None:
        self._build()
        index = LegalCorpusIndex(self.index_path)

        first = index.search("consumer compensation for deficient public services", "case", limit=2, candidate_limit=20)
        second = index.search("consumer compensation for deficient public services", "case", limit=2, candidate_limit=20)

        self.assertEqual(first, second)
        self.assertEqual(first[0].chunk_id, "case-2-c1")

    def test_runtime_merge_includes_provenance_and_does_not_scan_json(self) -> None:
        self._build()
        with patch.dict(
            os.environ,
            {
                "LEGAL_RAG_INDEX_PATH": str(self.index_path),
                "LEGAL_RAG_MAX_CASES": "2",
                "LEGAL_RAG_CORPUS_MAX_CASES": "2",
            },
        ), patch.object(Path, "glob", side_effect=AssertionError("runtime must not scan raw JSON")):
            result = retrieve_legal_rag_result("Kesavananda Bharati basic structure constitutional amendment")

        match = next(item for item in result.case_matches if "Kesavananda" in item.title)
        self.assertIn("json_judgements/constitutional.json", match.source_file)
        self.assertIn("case-1-c1", match.source_file)
        self.assertIn("judgements/kesavananda.pdf", match.source_file)
        self.assertIn("Supreme Court of India", match.reference)
        self.assertIn("p. 12", match.reference)

    def test_missing_or_incompatible_index_falls_back_to_curated_results(self) -> None:
        missing = self.root / "missing.sqlite3"
        with patch.dict(os.environ, {"LEGAL_RAG_INDEX_PATH": str(missing)}):
            result = retrieve_legal_rag_result("What is section 354 BNS?")

        self.assertEqual(result.statute_matches[0].reference, "Section 354")

    def test_failed_empty_build_does_not_replace_existing_index(self) -> None:
        self.index_path.write_bytes(b"existing-index")
        empty_root = self.root / "empty"
        empty_root.mkdir()

        with self.assertRaisesRegex(ValueError, "No valid corpus records"):
            build_corpus_index(empty_root, self.index_path)

        self.assertEqual(self.index_path.read_bytes(), b"existing-index")


if __name__ == "__main__":
    unittest.main()
