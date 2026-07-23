---
name: indian-mou-generator
description: Generate a memorandum of understanding from frontend inputs covering parties, intent, scope, responsibilities, timelines, commercial understanding, and binding or non-binding clauses.
---

# Memorandum of Understanding

Use this skill when `documentType` indicates MOU, memorandum of understanding, preliminary collaboration understanding, or heads-of-terms style document.

## Input mapping

- `partyDetails` -> party details
- `recipientDetails` -> counterparty details
- `caseDetails` -> purpose, collaboration scope, responsibilities, timelines, commercial understanding
- `relevantInfo` -> confidentiality, exclusivity, binding status, governing law, dispute resolution, annexures

## Output rules

1. Draft only the MOU.
2. Do not invent binding status or commercial commitments.
3. Use placeholders where scope or responsibilities are incomplete.
4. Clearly separate binding and non-binding clauses if relevant.
5. Keep wording collaborative but precise.

## Structure

1. Parties and background
2. Purpose
3. Scope and responsibilities
4. Timelines / commercials
5. Confidentiality / exclusivity if any
6. Binding effect / governing law
7. Signatures
