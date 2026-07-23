---
name: indian-evidence-affidavit-generator
description: Generate an affidavit of evidence or evidence-by-way-of-affidavit from frontend inputs covering witness identity, suit reference, exhibits, and evidentiary statements.
---

# Evidence by Way of Affidavit

Use this skill when `documentType` indicates evidence affidavit, affidavit in evidence, examination-in-chief affidavit, or proof affidavit in a civil matter.

## Input mapping

- `partyDetails` -> deponent / witness details
- `recipientDetails` -> opposite party or case-side details
- `caseDetails` -> case reference, witness role, factual testimony, exhibits, recovery claim or dispute facts
- `relevantInfo` -> exhibit marking, knowledge basis, dates, verification, place, annexures

## Output rules

1. Draft only the affidavit in evidence.
2. Do not invent exhibits or testimony facts.
3. Use placeholders where exhibit numbers or suit details are missing.
4. Keep statements evidence-focused and first-person where appropriate.
5. Avoid argument-heavy pleading style.

## Structure

1. Court heading and matter reference
2. Title
3. Witness introduction
4. Numbered evidentiary statements
5. Exhibit references
6. Verification
7. Signature / attestation placeholders
