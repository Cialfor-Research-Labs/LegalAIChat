---
name: indian-vendor-agreement-generator
description: Generate a vendor agreement from frontend inputs covering supply or service scope, pricing, delivery, quality, payment, warranties, and termination.
---

# Vendor Agreement

Use this skill when `documentType` indicates vendor agreement, supplier agreement, procurement contract, or supply-and-services vendor arrangement.

## Input mapping

- `partyDetails` -> customer and vendor details
- `recipientDetails` -> consignee or site details if relevant
- `caseDetails` -> goods or services, pricing, delivery timelines, specifications, payment terms
- `relevantInfo` -> SLAs, penalties, warranties, inspections, indemnity, confidentiality, compliance

## Output rules

1. Draft only the agreement.
2. Do not invent unit rates, volumes, or delivery schedules.
3. Use placeholders where commercial details are incomplete.
4. Keep supply obligations and quality control clauses explicit.
5. Separate goods and service obligations if both exist.

## Structure

1. Parties and recitals
2. Scope and specifications
3. Pricing and payment
4. Delivery and acceptance
5. Warranties and compliance
6. Indemnity, liability, termination
7. Signatures
