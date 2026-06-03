---
name: indian-writ-habeas-corpus-generator
description: Generate a writ petition for habeas corpus in Indian legal context from frontend inputs describing detention, custody, missing person circumstances, urgency, and release or production relief.
---

# Writ Petition for Habeas Corpus

Use this skill when `documentType` indicates writ of habeas corpus, illegal detention petition, unlawful custody petition, or prayer for production and release of a person.

## Input mapping

- `partyDetails` → petitioner details and relation to detained person
- `recipientDetails` → detaining authority, custodian, police officials, or private respondents
- `caseDetails` → detention facts, last-seen details, custody narrative, complaints made, urgency
- `relevantInfo` → age and identity of detenue, FIR or complaint details, medical issues, location clues, annexures

## Output rules

1. Draft only the writ petition.
2. Treat urgency and liberty interests seriously.
3. Do not invent detention facts or police records.
4. Use careful placeholders if custody details are incomplete.
5. Keep relief centered on production, protection, and release according to facts.

## Structure

1. Court heading
2. Cause title
3. Urgent introductory paragraph
4. Facts showing detention or unlawful restraint
5. Steps already taken with police / authorities, if supplied
6. Grounds
7. Interim urgent prayer
8. Final prayer for production and appropriate consequential orders
9. Verification

## Drafting guidance

- Differentiate state detention, police inaction, and private illegal custody.
- Avoid sensational language.
- If the person is a minor or vulnerable adult, foreground safety and welfare concerns.

## Frontend generation note

The document should preview as an urgent constitutional petition and leave unknown operational details as placeholders.
