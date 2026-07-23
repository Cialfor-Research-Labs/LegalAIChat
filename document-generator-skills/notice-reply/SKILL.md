---
name: indian-notice-reply-generator
description: Generate a reply to a legal notice from frontend inputs covering sender allegations, recipient response, denials, admissions, defences, and closing demands.
---

# Reply to Legal Notice

Use this skill when `documentType` indicates reply to legal notice, notice reply, response to demand notice, or advocate reply.

## Input mapping

- `partyDetails` -> replying party / client details
- `recipientDetails` -> original notice sender details
- `caseDetails` -> allegations made in the notice, factual response, denials, admissions, defence
- `relevantInfo` -> prior correspondence, settlement position, legal objections, documents, without-prejudice note

## Output rules

1. Draft only the notice reply.
2. Use Indian legal notice practice and formal advocate tone.
3. Do not invent admissions, denials, or legal provisions.
4. Use placeholders where the original notice content is incompletely described.
5. Keep rebuttals specific and structured.

## Structure

1. Advocate / sender details if supplied
2. Date and addressee
3. Subject
4. Introductory reply paragraph
5. Para-wise or issue-wise response
6. Defence / objections
7. Closing reservation of rights
8. Signature block
