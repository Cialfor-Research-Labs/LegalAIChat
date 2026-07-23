---
name: indian-software-development-agreement-generator
description: Generate a software development agreement from frontend inputs covering scope, milestones, deliverables, IP, acceptance, payment, support, and termination.
---

# Software Development Agreement

Use this skill when `documentType` indicates software development agreement, product build agreement, custom development contract, or technology services build contract.

## Input mapping

- `partyDetails` -> developer and client details
- `recipientDetails` -> subcontractor or affiliate details if relevant
- `caseDetails` -> project scope, deliverables, milestones, fees, timelines, acceptance
- `relevantInfo` -> IP ownership, source code escrow, confidentiality, warranty, support, penalties

## Output rules

1. Draft only the agreement.
2. Do not invent specifications, milestone dates, or payment terms.
3. Use placeholders for missing scope and delivery details.
4. Keep project execution and IP treatment explicit.
5. Avoid vague “best efforts” language when clear deliverable language is possible.

## Structure

1. Parties and recitals
2. Scope of services
3. Deliverables and milestones
4. Acceptance testing
5. Fees and payment
6. Change requests
7. IP and confidentiality
8. Warranty, support, liability
9. Termination
10. Signatures
