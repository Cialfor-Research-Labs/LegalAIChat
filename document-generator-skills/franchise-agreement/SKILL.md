---
name: indian-franchise-agreement-generator
description: Generate a franchise agreement from frontend inputs covering franchisor, franchisee, territory, fees, brand use, operations, training, and termination.
---

# Franchise Agreement

Use this skill when `documentType` indicates franchise agreement, franchise license, outlet franchise, or brand-operation franchise documentation.

## Input mapping

- `partyDetails` -> franchisor and franchisee details
- `recipientDetails` -> guarantor or affiliate details if relevant
- `caseDetails` -> territory, term, fees, setup obligations, operations standards, brand use
- `relevantInfo` -> training, audit, supply chain, non-compete, renewal, termination, dispute resolution

## Output rules

1. Draft only the agreement.
2. Do not invent franchise fees, territory rights, or support commitments.
3. Use placeholders where commercial terms are incomplete.
4. Keep control, compliance, and brand-protection clauses clear.
5. Avoid mixing this with a pure partnership format unless the input explicitly requires it.

## Structure

1. Parties and recitals
2. Grant of franchise
3. Territory and exclusivity
4. Fees and payments
5. Operational obligations
6. Brand and IP usage
7. Training and support
8. Inspections, defaults, termination
9. Post-termination obligations
10. Signatures
