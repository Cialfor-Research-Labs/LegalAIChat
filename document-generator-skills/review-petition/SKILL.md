---
name: indian-review-petition-generator
description: Generate an Indian review petition or review application based on frontend inputs describing the impugned order, error apparent, discovery of new matter, delay, and relief sought.
---

# Indian Review Petition / Review Application

Use this skill when `documentType` indicates review petition, review application, or prayer to review or recall an order or judgment before the same forum.

## Input mapping

- `partyDetails` → review petitioner / applicant details
- `recipientDetails` → respondent / opposite side details
- `caseDetails` → impugned order details, error alleged, new material, chronology, relief sought
- `relevantInfo` → case number, order date, delay explanation, limitation note, annexures, interim stay prayer

## Output rules

1. Draft only the review petition or application.
2. Keep the challenge narrow and review-specific.
3. Do not treat review as a full appeal.
4. Do not invent grounds like “error apparent” unless the input supports them.
5. Use placeholders for order dates, case numbers, and annexures if missing.

## Structure

1. Forum heading
2. Case title and review case title
3. Introductory statement identifying the impugned order
4. Brief facts
5. Grounds for review
6. Delay condonation note, if required
7. Prayer
8. Interim relief, if sought
9. Verification

## Drafting guidance

- Focus on patent error, omission, misreading, or discovery of material not earlier available, if supported.
- Avoid appellate-style re-argument unless necessary to explain the review ground.
- Keep prayer tailored to review, recall, modification, or rehearing.

## Frontend generation note

This output should remain compact and review-focused so later backend logic can route to court-specific formats.
