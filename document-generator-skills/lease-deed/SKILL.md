---
name: indian-lease-deed-generator
description: Generate a lease deed from frontend inputs covering lessor, lessee, property, rent, term, covenants, renewal, and possession terms.
---

# Lease Deed

Use this skill when `documentType` indicates lease deed, long-term lease, commercial lease, or registered lease-style property document.

## Input mapping

- `partyDetails` -> lessor and lessee details
- `recipientDetails` -> co-lessor, guarantor, or confirming party details
- `caseDetails` -> demised premises, term, rent, escalation, deposit, permitted use, possession
- `relevantInfo` -> registration, stamp duty, maintenance, taxes, assignment, renewal, default

## Output rules

1. Draft only the lease deed.
2. Do not invent survey numbers, rent escalation, or registration details.
3. Use placeholders where property or term details are absent.
4. Keep deed format formal and property-law oriented.
5. Separate covenants of lessor and lessee where useful.

## Structure

1. Title and parties
2. Recitals
3. Demised premises
4. Term, rent, deposit
5. Covenants
6. Repairs, taxes, compliance
7. Renewal, default, termination
8. Possession and handover
9. Execution and witnesses
