---
name: indian-interlocutory-application-generator
description: Generate an interlocutory application for Indian court proceedings using frontend inputs covering pending case details, interim relief sought, urgency, grounds, and prayer.
---

# Indian Interlocutory Application

Use this skill when `documentType` indicates an interlocutory application, interim application, I.A., miscellaneous application in a pending matter, or prayer for temporary procedural or interim relief.

## Input mapping

- `partyDetails` → applicant / petitioner details
- `recipientDetails` → respondent / opposite party details
- `caseDetails` → parent case details, interim relief sought, urgency, facts supporting interim relief
- `relevantInfo` → case number, stage of proceedings, statutory basis if known, annexures, affidavit support

## Output rules

1. Draft only the interlocutory application.
2. Link the application clearly to the main pending proceeding.
3. Do not invent procedural provisions.
4. Use placeholders where case number, stage, or relief specifics are missing.
5. Keep the prayer precise and short.

## Structure

1. Court heading
2. Main case reference
3. I.A. title
4. Applicant and respondent description
5. Short application opening
6. Grounds in numbered paragraphs
7. Urgency / balance of convenience / irreparable injury, where relevant
8. Prayer
9. Interim prayer, if separate
10. Verification / affidavit note, if supplied

## Drafting guidance

- Use this for stay, exemption, condonation, impleadment, amendment, additional documents, interim direction, or similar pending-case relief.
- If the exact subtype is unclear, draft a neutral interlocutory application with flexible prayer language.
- Avoid overloading the application with full merits unless necessary for interim relief.

## Frontend generation note

This should produce a clean application preview that can later be specialized by backend subtypes.
