---
name: indian-plaint-generator
description: Generate a civil plaint in Indian court format from frontend document-generator inputs such as parties, facts, cause of action, reliefs, valuation, jurisdiction, and annexure details.
---

# Indian Civil Plaint

Use this skill when `documentType` indicates a plaint, suit, civil suit plaint, money recovery suit, injunction suit, declaration suit, possession suit, or similar original civil pleading in Indian courts.

## Input mapping

- `partyDetails` → plaintiff details and plaintiff-side description
- `recipientDetails` → defendant details
- `caseDetails` → facts, cause of action, dates, transactions, breaches, relief sought
- `relevantInfo` → jurisdiction, valuation, limitation, interim relief, annexures, verification details

## Output rules

1. Draft only the plaint.
2. Use Indian legal context only.
3. Do not invent facts, dates, document numbers, or statutory provisions.
4. If a fact is missing, use restrained placeholders in square brackets.
5. Use formal court pleading language, not advisory commentary.

## Structure

Use this sequence unless the facts require a lawful variation:

1. Court heading
2. Title and cause title
3. Description of plaintiff and defendant
4. Introductory averments
5. Facts in chronological paragraphs
6. Cause of action
7. Jurisdiction
8. Limitation
9. Valuation for court fee and jurisdiction, if available
10. Relief clause
11. Interim relief, if supported
12. List of documents / annexures, if provided
13. Verification

## Drafting guidance

- Keep paragraphs numbered.
- State material facts, not evidence arguments.
- Reliefs must be specific and prayer-oriented.
- Mention court fee and valuation only if supplied or reasonably inferable from the user’s text.
- Do not cite sections casually; name the legal basis only when supported by the facts.

## Frontend generation note

The generated text should be ready for preview in the document generator and suitable for later backend templating.
