---
name: indian-written-statement-generator
description: Generate an Indian written statement in response to a plaint using frontend inputs containing party details, plaintiff claims, defendant version, preliminary objections, and prayer.
---

# Indian Written Statement

Use this skill when `documentType` indicates a written statement, defence, reply to plaint, or defendant pleading in a civil suit.

## Input mapping

- `partyDetails` → defendant details and defendant-side background
- `recipientDetails` → plaintiff details
- `caseDetails` → allegations to be answered, admissions, denials, defendant version, timeline
- `relevantInfo` → preliminary objections, jurisdiction objections, limitation objections, counter-claim note, annexures

## Output rules

1. Draft only the written statement.
2. Use Indian civil procedure context.
3. Avoid invented denials or admissions.
4. If plaint averments are incompletely described, use careful placeholders.
5. Keep the tone defensive, specific, and pleading-ready.

## Structure

1. Court heading
2. Cause title
3. Preliminary submissions / objections
4. Para-wise reply, where possible
5. Additional facts from defendant side
6. Objections on cause of action, jurisdiction, limitation, maintainability, if supported
7. Prayer
8. Verification

## Drafting guidance

- Prefer “contents of paragraph X are admitted / denied / matter of record” style when the input supports para-wise response.
- If the frontend input does not include para numbers, draft issue-wise replies instead.
- Avoid argumentative evidence narration unless needed to explain the defence.
- Mention set-off or counter-claim only if the facts support it.

## Frontend generation note

The output should work as a realistic preview draft and remain easy to convert later into structured backend output.
