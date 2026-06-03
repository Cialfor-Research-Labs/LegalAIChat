---
name: indian-contempt-petition-generator
description: Generate a contempt petition from frontend inputs covering prior order, disobedience, chronology, respondents, and relief sought.
---

# Contempt Petition

Use this skill when `documentType` indicates contempt petition, contempt application, wilful disobedience petition, or non-compliance with court order.

## Input mapping

- `partyDetails` -> petitioner / applicant details
- `recipientDetails` -> alleged contemnors / respondents
- `caseDetails` -> original order, obligations imposed, acts of disobedience, chronology, prejudice caused
- `relevantInfo` -> order date, case number, service of order, compliance correspondence, interim prayer

## Output rules

1. Draft only the contempt petition.
2. Do not invent court orders, service dates, or compliance failures.
3. Use placeholders where order details are missing.
4. Keep focus on wilful disobedience of an existing order.
5. Avoid merits re-argument unless needed to explain the order.

## Structure

1. Court heading and original case reference
2. Parties
3. Facts and prior order
4. Disobedience allegations
5. Grounds
6. Prayer
7. Verification
