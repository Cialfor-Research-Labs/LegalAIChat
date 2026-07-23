---
name: indian-independent-contractor-agreement-generator
description: Generate an independent contractor agreement from frontend inputs covering scope, service standards, fees, independence, confidentiality, IP, and termination.
---

# Independent Contractor Agreement

Use this skill when `documentType` indicates independent contractor agreement, contractor services agreement, or non-employee retained services contract.

## Input mapping

- `partyDetails` -> principal and contractor details
- `recipientDetails` -> site or project contact details if relevant
- `caseDetails` -> services, service levels, fees, term, reporting, tools, reimbursements
- `relevantInfo` -> tax treatment, IP ownership, confidentiality, non-solicit, liability, termination

## Output rules

1. Draft only the agreement.
2. Do not invent contractor fees, term, or exclusivity.
3. Use placeholders for missing commercial terms.
4. Preserve non-employment status clearly.
5. Keep scope and liability provisions practical.

## Structure

1. Parties and recitals
2. Services and standards
3. Fees and expenses
4. Independent status
5. Confidentiality and IP
6. Compliance, indemnity, termination
7. Signatures
