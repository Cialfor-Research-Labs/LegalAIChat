---
name: indian-consultancy-agreement-generator
description: Generate a consultancy agreement from frontend inputs covering consultant scope, deliverables, fees, confidentiality, IP, and termination.
---

# Consultancy Agreement

Use this skill when `documentType` indicates consultancy agreement, advisory services agreement, consultant retainer, or independent consulting contract.

## Input mapping

- `partyDetails` -> client and consultant details
- `recipientDetails` -> affiliate or project contact details if relevant
- `caseDetails` -> scope, term, deliverables, fees, reimbursement, reporting, acceptance
- `relevantInfo` -> confidentiality, IP, non-solicit, tax treatment, liability, dispute resolution

## Output rules

1. Draft only the agreement.
2. Do not invent fees, deliverables, or tax status.
3. Use placeholders where scope or payment terms are missing.
4. Keep independence and service scope clear.
5. Avoid employer-employee language unless the input requires it.

## Structure

1. Parties and recitals
2. Scope of services
3. Term and deliverables
4. Fees and expenses
5. Confidentiality and IP
6. Independent contractor status
7. Liability and termination
8. Signatures
