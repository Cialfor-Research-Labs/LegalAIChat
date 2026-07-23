---
name: indian-software-license-agreement-generator
description: Generate a software license agreement for Indian commercial use from frontend inputs covering licensor, licensee, scope, restrictions, fees, IP, support, and termination.
---

# Software License Agreement

Use this skill when `documentType` indicates software license agreement, on-prem software license, enterprise software license, or technology licensing contract.

## Input mapping

- `partyDetails` -> licensor and licensee details
- `recipientDetails` -> affiliates or implementation partners if relevant
- `caseDetails` -> licensed software, scope, users, territory, fees, term, support
- `relevantInfo` -> IP ownership, warranties, limitation of liability, audit, confidentiality, compliance

## Output rules

1. Draft only the agreement.
2. Do not invent pricing, seat counts, uptime commitments, or IP ownership exceptions.
3. Use placeholders where commercial terms are incomplete.
4. Keep clauses precise and technology-contract oriented.
5. Preserve confidentiality and IP provisions clearly.

## Structure

1. Parties and recitals
2. Definitions
3. License grant and restrictions
4. Fees and payment
5. Support and maintenance
6. IP ownership
7. Confidentiality and data clauses
8. Warranties, disclaimers, liability
9. Termination
10. Dispute resolution and signatures
