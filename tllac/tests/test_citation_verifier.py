from __future__ import annotations

import unittest

from tllac.app.services.citation_verifier import (
    EvidenceSource,
    ResearchClaim,
    ResearchDraft,
    SourceMapping,
    parse_research_draft,
    verify_research_draft,
)


class CitationVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = EvidenceSource(
            source_id="LC-123",
            source_type="legal-statute",
            title="BNS",
            citation="BNS Section 138",
            court="",
            date="",
            section="Section 138",
            page="",
            paragraph="",
            url="",
            extracted_text="Section 138 applies to dishonour of cheque.",
        )

    def test_verifies_claims_with_known_sources(self) -> None:
        draft = ResearchDraft(
            memo_title="Cheque Dishonour Research",
            memo_summary="Section 138 applies.",
            confidence=0.92,
            claims=[
                ResearchClaim(
                    claim_id="C1",
                    text="Section 138 applies to cheque dishonour.",
                    source_ids=["LC-123"],
                    source_locations=["section:138"],
                    material=True,
                    confidence=0.9,
                )
            ],
            source_mappings=[
                SourceMapping(source_id="LC-123", claim_ids=["C1"], support="Statutory basis."),
            ],
        )

        result = verify_research_draft(draft, [self.source])

        self.assertTrue(result.verified)
        self.assertFalse(result.review_required)
        self.assertEqual(len(result.claims), 1)
        self.assertEqual(result.claims[0].claim_id, "C1")

    def test_rejects_unknown_source_ids_and_unsupported_claims(self) -> None:
        draft = ResearchDraft(
            memo_title="Fake Memo",
            memo_summary="Unsupported memo.",
            confidence=0.2,
            claims=[
                ResearchClaim(
                    claim_id="C1",
                    text="This is a fabricated legal claim.",
                    source_ids=["FAKE-1"],
                    source_locations=["section:999"],
                    material=True,
                ),
                ResearchClaim(
                    claim_id="C2",
                    text="Material claim without citation.",
                    source_ids=[],
                    material=True,
                ),
            ],
            source_mappings=[
                SourceMapping(source_id="FAKE-1", claim_ids=["C1"], support="Invented support."),
            ],
        )

        result = verify_research_draft(draft, [self.source])

        self.assertFalse(result.verified)
        self.assertTrue(result.review_required)
        self.assertEqual(result.claims, [])
        self.assertGreaterEqual(len(result.rejected_claims), 2)

    def test_parse_research_draft_handles_json_payload(self) -> None:
        payload = """
        {
          "memo_title": "Parsed Memo",
          "memo_summary": "Summary",
          "confidence": 0.75,
          "claims": [
            {"claim_id": "C1", "text": "Claim", "source_ids": ["LC-123"], "material": true}
          ],
          "source_mappings": [
            {"source_id": "LC-123", "claim_ids": ["C1"], "support": "Ok"}
          ],
          "review_notes": "none"
        }
        """

        draft = parse_research_draft(payload)

        self.assertEqual(draft.memo_title, "Parsed Memo")
        self.assertEqual(draft.claims[0].claim_id, "C1")


if __name__ == "__main__":
    unittest.main()
