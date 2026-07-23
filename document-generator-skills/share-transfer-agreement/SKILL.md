---
name: indian-share-transfer-agreement-generator
description: Generate a share transfer agreement for Indian corporate transactions from frontend inputs covering transferor, transferee, company, consideration, warranties, and closing mechanics.
---

# Share Transfer Agreement

Use this skill when `documentType` indicates share transfer agreement, private share sale, transfer of shares, or secondary transfer in a company.

## Input mapping

- `partyDetails` -> transferor, transferee, and company details
- `recipientDetails` -> additional parties or confirming parties
- `caseDetails` -> class and number of shares, consideration, closing, restrictions, consents
- `relevantInfo` -> warranties, indemnities, governing law, stamp duty, board approval notes

## Output rules

1. Draft only the agreement.
2. Do not invent share numbers, consideration, or corporate approvals.
3. Use placeholders where transaction specifics are missing.
4. Keep it corporate-transaction focused and clause-based.
5. Mention company-law compliance only where supported by the input.

## Structure

1. Title, date, parties
2. Recitals
3. Definitions, if needed
4. Sale and transfer of shares
5. Consideration and payment
6. Closing mechanics
7. Representations and warranties
8. Covenants and indemnities
9. Governing law and dispute resolution
10. Signature blocks
