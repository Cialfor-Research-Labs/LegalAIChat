---
name: indian-writ-mandamus-generator
description: Generate a writ petition for mandamus in Indian legal context from frontend inputs describing a public duty, refusal, inaction, representation made, and relief seeking a direction.
---

# Writ Petition for Mandamus

Use this skill when `documentType` indicates writ of mandamus or a petition seeking a direction to a public authority to perform a statutory, public, or legal duty.

## Input mapping

- `partyDetails` → petitioner details
- `recipientDetails` → respondent department, authority, officer, or statutory body
- `caseDetails` → duty owed, application or representation made, refusal or inaction, resulting prejudice
- `relevantInfo` → relevant dates, reminders, policy references, documents, interim urgency

## Output rules

1. Draft only the writ petition.
2. Focus on enforceable public duty and failure to act.
3. Do not invent statutory obligations.
4. Use placeholders if representations, dates, or orders are not fully described.
5. Keep the prayer direction-specific.

## Structure

1. Court heading
2. Cause title
3. Facts and petitioner grievance
4. Public duty and respondent default
5. Representations already made
6. Grounds
7. Interim prayer, if needed
8. Final prayer for direction / consideration / disposal within time
9. Verification

## Drafting guidance

- Mandamus is usually for compelling action, not quashing an order.
- If the user wants both quashing and direction, note both only when facts support combined relief.
- Ask for time-bound disposal where appropriate.

## Frontend generation note

The generated text should be straightforward, authority-focused, and ready for later backend enforcement templates.
