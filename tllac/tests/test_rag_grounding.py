import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tllac"))

from app.services.chat_grounding_service import sanitize_grounded_response
from app.services.legal_rag_service import (
    build_legal_rag_context_from_result,
    LegalRagResult,
    RetrievedAuthority,
    normalize_legal_rag_query,
    retrieve_legal_rag_result,
)


class LegalRagConsistencyTests(unittest.TestCase):
    def test_normalize_legal_rag_query_collapses_whitespace(self) -> None:
        self.assertEqual(
            normalize_legal_rag_query("  What   is   Section  354   BNS?  "),
            "What is Section 354 BNS?",
        )

    def test_retrieve_legal_rag_result_is_stable_for_same_query(self) -> None:
        query = "A drunk driver hit my bike and I got injured, what legal action can I take?"

        first = retrieve_legal_rag_result(query)
        second = retrieve_legal_rag_result(query)

        self.assertEqual(
            [(item.reference, item.score) for item in first.statute_matches],
            [(item.reference, item.score) for item in second.statute_matches],
        )
        self.assertEqual(
            [(item.title, item.reference, item.score) for item in first.case_matches],
            [(item.title, item.reference, item.score) for item in second.case_matches],
        )

    def test_retrieve_legal_rag_result_is_stable_for_normalized_query_variants(self) -> None:
        first = retrieve_legal_rag_result("What is section 354 BNS?")
        second = retrieve_legal_rag_result("  What is   section 354   BNS? ")

        self.assertEqual(
            [item.reference for item in first.statute_matches],
            [item.reference for item in second.statute_matches],
        )
        self.assertEqual(
            [item.title for item in first.case_matches],
            [item.title for item in second.case_matches],
        )

    def test_empty_retrieval_produces_low_confidence_and_insufficient_context(self) -> None:
        result = retrieve_legal_rag_result("flibbertigibbet")

        self.assertFalse(result.statute_matches)
        self.assertFalse(result.case_matches)
        self.assertLess(result.confidence, 0.1)
        self.assertIn(
            "The retrieved legal documents do not contain sufficient information",
            build_legal_rag_context_from_result(result),
        )

    def test_exact_section_query_does_not_fall_back_to_numeric_prefixes(self) -> None:
        result = retrieve_legal_rag_result("What is section 354 BNS?")

        self.assertEqual(len(result.statute_matches), 1)
        self.assertEqual(result.statute_matches[0].reference, "Section 354")
        self.assertIn("BNS", result.statute_matches[0].title)

    def test_exact_act_and_section_query_stays_within_requested_act(self) -> None:
        result = retrieve_legal_rag_result("Explain section 125 BNS")

        self.assertGreaterEqual(len(result.statute_matches), 1)
        self.assertEqual(result.statute_matches[0].reference, "Section 125")
        self.assertIn("BNS", result.statute_matches[0].title)

    def test_false_case_query_surfaces_actionable_bns_bnss_bsa_sections(self) -> None:
        result = retrieve_legal_rag_result(
            "My wife is threatening to file a false dowry case against me. What sections apply and what should I do?"
        )

        references = {(item.act_key, item.reference) for item in result.statute_matches}
        self.assertIn(("bns", "Section 248"), references)
        self.assertIn(("bnss", "Section 482"), references)
        self.assertTrue(any(item.act_key == "bsa" for item in result.statute_matches))


class GroundingSanitizerTests(unittest.TestCase):
    def _make_rag_result(self) -> LegalRagResult:
        return LegalRagResult(
            query="A drunk driver hit my bike and I got injured, what legal action can I take?",
            statute_matches=(
                RetrievedAuthority(
                    authority_type="statute",
                    title="Bharatiya Nyaya Sanhita, 2023",
                    reference="Section 281",
                    summary="Rash driving on a public way.",
                    score=20.0,
                    source_file="tllac/app/data/statute_sections.json",
                ),
            ),
            case_matches=(
                RetrievedAuthority(
                    authority_type="case",
                    title="N.K.V. Bros. (P) Ltd. v. M. Karumai Ammal",
                    reference="Supreme Court of India (1980)",
                    summary="Motor accident claims should not be defeated through technicalities.",
                    score=7.75,
                    source_file="tllac/app/data/case_law_corpus.json",
                ),
            ),
        )

    def test_sanitizer_replaces_unsupported_section_numbers(self) -> None:
        sanitized = sanitize_grounded_response(
            "You can proceed under BNS Section 304 and seek compensation.",
            current_query="A drunk driver hit my bike and I got injured, what legal action can I take?",
            rag_result=self._make_rag_result(),
        )

        self.assertNotIn("Section 304", sanitized)
        self.assertIn("exact current statutory provision should be verified", sanitized)
        self.assertIn("Verification Note:", sanitized)

    def test_sanitizer_allows_user_supplied_section_numbers(self) -> None:
        sanitized = sanitize_grounded_response(
            "Section 125 can apply only if the facts support endangering life or personal safety.",
            current_query="Does Section 125 apply here?",
            rag_result=LegalRagResult(query="Does Section 125 apply here?", statute_matches=(), case_matches=()),
        )

        self.assertIn("Section 125", sanitized)

    def test_sanitizer_allows_retrieved_sections_and_blocks_unrelated_ones(self) -> None:
        sanitized = sanitize_grounded_response(
            "BNS Section 281 is relevant here, but Section 125 also definitely applies.",
            current_query="A drunk driver hit my bike and I got injured, what legal action can I take?",
            rag_result=self._make_rag_result(),
        )

        self.assertIn("Section 281", sanitized)
        self.assertNotIn("Section 125", sanitized)
        self.assertIn("exact current statutory provision should be verified", sanitized)

    def test_sanitizer_allows_sections_found_in_retrieved_statute_text(self) -> None:
        rag_result = LegalRagResult(
            query="Which provision covers contracts that cannot be specifically enforced?",
            statute_matches=(
                RetrievedAuthority(
                    authority_type="statute",
                    title="The Specific Relief Act, 1963",
                    reference="Chunk law-1-c1",
                    summary="Section 14 identifies contracts which cannot be specifically enforced.",
                    score=8.0,
                    source_file="json_law_files/specific-relief.json [law-1-c1]",
                ),
            ),
            case_matches=(),
        )

        sanitized = sanitize_grounded_response(
            "Section 14 addresses contracts that cannot be specifically enforced.",
            current_query=rag_result.query,
            rag_result=rag_result,
        )

        self.assertIn("Section 14", sanitized)
        self.assertNotIn("exact current statutory provision should be verified", sanitized)

    def test_sanitizer_removes_old_placeholder_phrase(self) -> None:
        sanitized = sanitize_grounded_response(
            "Risk of false accusation under the relevant section of the applicable statute (equivalent to IPC 498A).",
            current_query="My wife is threatening to file a false dowry case against me.",
            rag_result=LegalRagResult(query="My wife is threatening to file a false dowry case against me.", statute_matches=(), case_matches=()),
        )

        self.assertNotIn("the relevant section of the applicable statute", sanitized)

    def test_sanitizer_restores_heading_line_breaks(self) -> None:
        sanitized = sanitize_grounded_response(
            "Classification: Criminal defence Intake Extraction: Known Facts Key Issues: Possible counter-action under BNS Section 248. Remedies and Forum: - Apply for anticipatory bail. Disclaimer: General guidance only.",
            current_query="My wife is threatening to file a false dowry case against me.",
            rag_result=LegalRagResult(query="My wife is threatening to file a false dowry case against me.", statute_matches=(), case_matches=()),
        )

        self.assertIn("Classification:", sanitized)
        self.assertIn("\n\nIntake Extraction:", sanitized)
        self.assertIn("\n\nKey Issues:", sanitized)
        self.assertIn("\n\nRemedies and Forum:", sanitized)
        self.assertIn("\n- Apply for anticipatory bail.", sanitized)

    def test_sanitizer_repairs_broken_bold_headings(self) -> None:
        sanitized = sanitize_grounded_response(
            "Legal Analysis: False Dowry Case Threat by Wife\n**1.\nShort Classification** Domain: Criminal Law\n**\n\nKnown Facts:**\n\nWife is threatening to file a false case.",
            current_query="My wife is threatening to file a false dowry case against me.",
            rag_result=LegalRagResult(query="My wife is threatening to file a false dowry case against me.", statute_matches=(), case_matches=()),
        )

        self.assertIn("**1. Short Classification**", sanitized)
        self.assertNotIn("**1.\nShort Classification**", sanitized)
        self.assertNotIn("\n**\n", sanitized)

    def test_sanitizer_restores_dash_section_formatting(self) -> None:
        sanitized = sanitize_grounded_response(
            "Opening Your wife's threat is serious. --- Intake Extraction- Parties: Husband and wife --- Key Issues1. Risk of false case. 2. Need bail. --- Relevant Law1. BNS Section 248 applies. 2. BNSS Section 482 applies.",
            current_query="My wife is threatening to file a false dowry case against me.",
            rag_result=LegalRagResult(query="My wife is threatening to file a false dowry case against me.", statute_matches=(), case_matches=()),
        )

        self.assertIn("Opening\n", sanitized)
        self.assertIn("Intake Extraction", sanitized)
        self.assertIn("Key Issues", sanitized)
        self.assertIn("\n1. Risk of false case.", sanitized)
        self.assertIn("\n2. Need bail.", sanitized)
        self.assertIn("Relevant Law", sanitized)

    def test_sanitizer_restores_markdown_headings_bullets_and_tables(self) -> None:
        sanitized = sanitize_grounded_response(
            "Legal Analysis: False Dowry Case Threat by Wife#### 1. Intake Extraction\nKnown Facts:- Wife is threatening to file a false dowry case.\n#### 2. Evidence Matrix| Evidence Type | Why It Matters |\n|------------------|-------------------| | Marriage certificate | Proof |",
            current_query="My wife is threatening to file a false dowry case against me.",
            rag_result=LegalRagResult(query="My wife is threatening to file a false dowry case against me.", statute_matches=(), case_matches=()),
        )

        self.assertIn("\n\n#### 1. Intake Extraction", sanitized)
        self.assertIn("Known Facts:\n- Wife is threatening to file a false dowry case.", sanitized)
        self.assertIn("\n\n#### 2. Evidence Matrix", sanitized)
        self.assertIn("| Evidence Type | Why It Matters |", sanitized)
        self.assertIn("|------------------|-------------------|", sanitized)

    def test_sanitizer_replaces_unsupported_case_titles(self) -> None:
        sanitized = sanitize_grounded_response(
            "The Supreme Court in Imaginary Case v. State of India already settled this issue.",
            current_query="A drunk driver hit my bike and I got injured, what legal action can I take?",
            rag_result=self._make_rag_result(),
        )

        self.assertNotIn("Imaginary Case v. State of India", sanitized)
        self.assertIn("reported decision that should be verified", sanitized)


if __name__ == "__main__":
    unittest.main()
