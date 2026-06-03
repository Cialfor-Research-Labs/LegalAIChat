---
name: indian-rent-agreement-generator
description: Generate a residential or commercial rent agreement from frontend inputs covering landlord, tenant, premises, rent, deposit, term, and use conditions.
---

# Rent Agreement

Use this skill when `documentType` indicates rent agreement, leave and license style rental draft, tenancy draft, or short occupancy contract.

## Input mapping

- `partyDetails` -> landlord and tenant details
- `recipientDetails` -> co-occupant or confirming party details if relevant
- `caseDetails` -> premises, rent, security deposit, term, lock-in, utility, maintenance
- `relevantInfo` -> police verification, notice period, renewal, restrictions, furnishing inventory

## Output rules

1. Draft only the agreement.
2. Do not invent address, rent, deposit, or registration facts.
3. Use placeholders where property particulars are missing.
4. Keep premises use and possession clauses clear.
5. Use Indian rental context and neutral property language.

## Structure

1. Parties and premises details
2. Term and possession
3. Rent and deposit
4. Utilities and maintenance
5. Use restrictions
6. Notice, termination, handover
7. Signatures and witness blocks
