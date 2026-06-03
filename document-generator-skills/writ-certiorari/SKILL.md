---
name: indian-writ-certiorari-generator
description: Generate a writ petition for certiorari in Indian constitutional practice from frontend inputs describing the impugned order, authority, jurisdictional error, procedural illegality, and relief.
---

# Writ Petition for Certiorari

Use this skill when `documentType` indicates writ of certiorari or a petition seeking quashing of an order, decision, proceeding, or adjudicatory action of a public authority, tribunal, or quasi-judicial body.

## Input mapping

- `partyDetails` → petitioner details
- `recipientDetails` → respondent authority and affected parties
- `caseDetails` → impugned order, facts, procedural history, illegality, jurisdictional defect
- `relevantInfo` → forum, constitutional basis if known, annexures, delay explanation, interim stay

## Output rules

1. Draft only the writ petition.
2. Use Indian constitutional and public law context.
3. Do not invent constitutional articles or statutory provisions.
4. Keep grounds centered on illegality, lack of jurisdiction, breach of natural justice, perversity, or procedural error if supported.
5. Use placeholders where order details or dates are missing.

## Structure

1. High Court / Supreme Court heading, if supplied
2. Cause title
3. Synopsis-style introduction, if useful
4. Facts
5. Grounds
6. Maintainability / lack of alternate remedy note, if supported
7. Interim relief
8. Final prayer for quashing and consequential directions
9. Verification

## Drafting guidance

- Certiorari is primarily for quashing an impugned decision.
- Identify the authority, impugned action, and defect clearly.
- Ask for production of records only if the input suggests it.

## Frontend generation note

The output should read like a public-law petition preview and remain adaptable for later court-specific backend formatting.
