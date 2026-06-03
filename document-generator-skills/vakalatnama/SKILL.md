---
name: indian-vakalatnama-generator
description: Generate a vakalatnama format for Indian litigation from frontend inputs containing client identity, advocate details, matter reference, and execution details.
---

# Indian Vakalatnama

Use this skill when `documentType` indicates vakalatnama, memo of appearance authority, or authorization of advocate in an Indian court or tribunal matter.

## Input mapping

- `partyDetails` → client / executant details
- `recipientDetails` → opposite party details or case title reference
- `caseDetails` → matter description, forum, case number, advocate authorization context
- `relevantInfo` → advocate name, enrollment details if supplied, address for service, witness details, execution place and date

## Output rules

1. Draft only the vakalatnama text.
2. Use Indian litigation authority language.
3. Do not invent advocate enrollment or stamp details.
4. Keep placeholders for signatures, identification, acceptance by advocate, witness, and welfare stamp areas.
5. Do not convert vakalatnama into a narrative pleading.

## Structure

1. Court / tribunal heading
2. Cause title or matter title
3. Vakalatnama heading
4. Authority clause appointing advocate(s)
5. Powers granted to act, appear, file, receive, compromise where lawfully standard
6. Client execution block
7. Advocate acceptance block
8. Witness / identification placeholders

## Drafting guidance

- Preserve standard vakalatnama tone.
- Keep authority clauses broad but conventional.
- Mention multiple advocates only if the input indicates that.

## Frontend generation note

The preview should be text-first and placeholder-friendly, since final stamping and signature layout will likely be handled later.
