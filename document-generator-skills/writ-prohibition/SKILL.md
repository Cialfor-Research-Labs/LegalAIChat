---
name: indian-writ-prohibition-generator
description: Generate a writ petition for prohibition in Indian legal context from frontend inputs describing a subordinate court or tribunal acting without jurisdiction or beyond lawful authority.
---

# Writ Petition for Prohibition

Use this skill when `documentType` indicates writ of prohibition or a petition seeking to restrain a subordinate court, tribunal, or quasi-judicial body from continuing proceedings without jurisdiction.

## Input mapping

- `partyDetails` → petitioner details
- `recipientDetails` → tribunal, authority, and contesting parties
- `caseDetails` → pending proceedings, jurisdictional error, threatened excess of authority, stage of proceedings
- `relevantInfo` → case number, notices, interim stay need, annexures

## Output rules

1. Draft only the writ petition.
2. Keep it prospective and restraint-focused.
3. Do not convert it into an appeal on merits.
4. Do not invent jurisdictional defects.
5. Use placeholders where proceeding numbers or dates are missing.

## Structure

1. Court heading
2. Cause title
3. Details of impugned ongoing proceeding
4. Facts showing absence or excess of jurisdiction
5. Grounds
6. Interim prayer for stay of further proceedings
7. Final prayer restraining continuation
8. Verification

## Drafting guidance

- Prohibition is aimed at stopping unlawful continuation of proceedings.
- Emphasize jurisdiction, competence, and procedural unlawfulness.
- Avoid detailed factual trial issues unless they establish jurisdictional overreach.

## Frontend generation note

The output should remain narrow and procedural so it can later fit a backend writ-petition formatter.
