---
name: indian-affidavit-generator
description: Generate an Indian affidavit format from frontend inputs including deponent identity, factual statements, document references, verification, and attestation placeholders.
---

# Indian Affidavit

Use this skill when `documentType` indicates an affidavit, supporting affidavit, sworn statement, or verification affidavit in an Indian legal matter.

## Input mapping

- `partyDetails` → deponent details
- `recipientDetails` → opposite party or case-side reference, if relevant
- `caseDetails` → factual statements to be affirmed
- `relevantInfo` → case number, forum, annexures, identification details, place, date, verification points

## Output rules

1. Draft only the affidavit text.
2. Use first-person deponent language where appropriate.
3. Do not fabricate oath, notary, or attestation particulars.
4. Use placeholders for verification date, place, identification, oath commissioner details, and exhibits if missing.
5. Keep the contents factual and affirmation-oriented.

## Structure

1. Forum heading, if supplied
2. Case title / matter reference
3. Title: Affidavit
4. Deponent introduction
5. Numbered factual affirmations
6. Statement of truth / verification
7. Deponent signature block
8. Attestation placeholder block

## Drafting guidance

- Use “I say that…” style sparingly and clearly.
- Separate personal knowledge statements from records-based statements if the facts show that distinction.
- Keep legal arguments minimal unless it is expressly a supporting affidavit for a petition or application.

## Frontend generation note

The text should remain plain enough for preview while preserving affidavit structure for later formatting and attestation workflows.
