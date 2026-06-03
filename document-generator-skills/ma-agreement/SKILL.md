---
name: indian-ma-agreement-generator
description: Generate an M&A agreement, business acquisition agreement, or share purchase transaction draft from frontend inputs covering target, buyer, seller, consideration, diligence, conditions, and closing.
---

# M&A / Acquisition Agreement

Use this skill when `documentType` indicates merger and acquisition agreement, acquisition agreement, business transfer, share purchase in control transaction, or similar M&A documentation.

## Input mapping

- `partyDetails` -> buyer, seller, target details
- `recipientDetails` -> additional stakeholders or guarantors
- `caseDetails` -> transaction structure, consideration, assets or shares, closing conditions, timeline
- `relevantInfo` -> due diligence issues, warranties, indemnities, regulatory approvals, schedules

## Output rules

1. Draft only the transaction document requested.
2. Do not invent transaction values, schedules, or approval status.
3. Use placeholders for commercial terms not provided.
4. Keep drafting formal, detailed, and transaction-structured.
5. Avoid overcommitting on tax or regulatory advice unless the user supplies specifics.

## Structure

1. Title and parties
2. Recitals
3. Definitions
4. Transaction mechanics
5. Consideration
6. Conditions precedent
7. Closing and post-closing obligations
8. Representations, warranties, indemnities
9. Confidentiality and restrictive covenants
10. Governing law and dispute resolution
11. Signatures
