---
name: indian-saas-agreement-generator
description: Generate a SaaS agreement from frontend inputs covering subscription services, access rights, fees, data handling, support, uptime, and termination.
---

# SaaS Agreement

Use this skill when `documentType` indicates SaaS agreement, cloud software subscription agreement, hosted platform agreement, or subscription services contract.

## Input mapping

- `partyDetails` -> provider and customer details
- `recipientDetails` -> implementation partner or affiliate details if relevant
- `caseDetails` -> services, subscription model, users, fees, term, service levels
- `relevantInfo` -> data protection, confidentiality, uptime, support, transition assistance, governing law

## Output rules

1. Draft only the SaaS agreement.
2. Do not invent service levels, fees, or data-processing commitments.
3. Use placeholders for commercial and technical specifics that are missing.
4. Keep cloud-service clauses practical and readable.
5. Separate access, data, support, and liability topics clearly.

## Structure

1. Parties and recitals
2. Definitions
3. Subscription and access rights
4. Fees and billing
5. Customer obligations
6. Support / service levels
7. Data, confidentiality, IP
8. Warranties and limitation of liability
9. Suspension / termination / exit
10. General clauses and signatures
