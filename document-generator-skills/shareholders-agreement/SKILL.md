---
name: indian-shareholders-agreement-generator
description: Generate a shareholders agreement from frontend inputs covering shareholders, shareholding, governance, reserved matters, transfer restrictions, and exit rights.
---

# Shareholders Agreement

Use this skill when `documentType` indicates shareholders agreement, SHA, founders SHA, investor rights agreement, or governance/share-transfer rights document.

## Input mapping

- `partyDetails` -> company, founders, shareholders, investors
- `recipientDetails` -> affiliates or nominees if relevant
- `caseDetails` -> ownership structure, board rights, reserved matters, transfer restrictions, exit rights
- `relevantInfo` -> vesting, anti-dilution, information rights, deadlock, dispute resolution, schedules

## Output rules

1. Draft only the agreement.
2. Do not invent capitalization data or investor rights.
3. Use placeholders where economics or governance details are missing.
4. Keep corporate governance and transfer rights clear.
5. Match startup and private-company transaction style.

## Structure

1. Parties and recitals
2. Definitions
3. Shareholding and capital structure
4. Board and governance rights
5. Reserved matters
6. Transfer restrictions and exit rights
7. Founder obligations / vesting, if applicable
8. Confidentiality, non-compete, dispute clauses
9. Signatures
