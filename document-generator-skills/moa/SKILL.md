---
name: indian-moa-generator
description: Generate a Memorandum of Association or MOA-style company constitutional draft from frontend inputs covering company name, objects, liability, share capital, and subscriber details.
---

# Memorandum of Association

Use this skill when `documentType` indicates MOA, memorandum of association, company objects document, or incorporation constitutional draft.

## Input mapping

- `partyDetails` -> company and subscriber details
- `recipientDetails` -> authority or registrar context if relevant
- `caseDetails` -> company name, state, object clauses, liability, capital structure
- `relevantInfo` -> subscriber sheet, witness details, company type, sector notes

## Output rules

1. Draft only the MOA text.
2. Do not invent official company details or subscriber data.
3. Use placeholders for share capital, state, and subscriber particulars if missing.
4. Keep objects and constitutional clauses formal and company-law styled.
5. Avoid mixing in Articles of Association content unless explicitly requested.

## Structure

1. Company name clause
2. Registered office state clause
3. Object clauses
4. Liability clause
5. Share capital clause
6. Subscription sheet
