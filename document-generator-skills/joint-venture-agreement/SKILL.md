---
name: indian-joint-venture-agreement-generator
description: Generate a joint venture agreement from frontend inputs covering venture purpose, contributions, governance, profit sharing, IP, responsibilities, and exit.
---

# Joint Venture Agreement

Use this skill when `documentType` indicates JV agreement, joint venture agreement, strategic collaboration with shared control, or venture-operation contract.

## Input mapping

- `partyDetails` -> JV parties and venture details
- `recipientDetails` -> affiliates, guarantors, or project entities if relevant
- `caseDetails` -> purpose, scope, contribution, ownership, governance, profit sharing, management
- `relevantInfo` -> IP, exclusivity, deadlock, funding, exit, termination, dispute resolution

## Output rules

1. Draft only the JV agreement.
2. Do not invent ownership ratios or financial commitments.
3. Use placeholders for missing governance and economic terms.
4. Keep commercial collaboration and governance balanced.
5. Clarify whether the JV is contractual or entity-based if the input says so.

## Structure

1. Parties and recitals
2. Purpose and scope
3. Contributions
4. Governance and management
5. Funding / profit sharing
6. IP, confidentiality, exclusivity
7. Deadlock, exit, termination
8. Signatures
