---
name: indian-freelance-agreement-generator
description: Generate a freelance agreement from frontend inputs covering project scope, fees, deadlines, ownership, confidentiality, and termination.
---

# Freelance Agreement

Use this skill when `documentType` indicates freelance agreement, project freelancer contract, gig engagement, or one-off independent work agreement.

## Input mapping

- `partyDetails` -> client and freelancer details
- `recipientDetails` -> project manager or affiliate details if relevant
- `caseDetails` -> work scope, deliverables, deadlines, fees, revisions, acceptance
- `relevantInfo` -> IP assignment, confidentiality, taxes, portfolio use, termination, disputes

## Output rules

1. Draft only the agreement.
2. Do not invent milestones, rates, or ownership terms.
3. Use placeholders where project specifics are missing.
4. Keep the document concise and operational.
5. Preserve independent-contractor tone.

## Structure

1. Parties and project description
2. Deliverables and timeline
3. Fees and invoices
4. IP and confidentiality
5. Revisions and acceptance
6. Termination and dispute clauses
7. Signatures
