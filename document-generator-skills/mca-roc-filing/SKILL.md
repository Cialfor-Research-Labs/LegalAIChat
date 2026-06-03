---
name: indian-mca-roc-filing-generator
description: Generate an MCA or ROC filing draft, covering board/company particulars, event details, resolutions, and filing statements from frontend inputs.
---

# MCA / ROC Filing Draft

Use this skill when `documentType` indicates MCA filing, ROC filing, corporate compliance filing, or supporting draft for Companies Act compliance submissions.

## Input mapping

- `partyDetails` -> company details
- `recipientDetails` -> ROC / MCA / authority details if relevant
- `caseDetails` -> filing event, corporate action, dates, resolutions, particulars to be filed
- `relevantInfo` -> form number, attachments, signatory details, compliance notes

## Output rules

1. Draft only the filing text, covering letter, or statement requested by the inputs.
2. Do not invent statutory form numbers or filing dates.
3. Use placeholders for CIN, SRN, DIN, board resolution dates, and attachments if absent.
4. Keep style compliance-focused and factual.
5. Avoid unsupported legal conclusions.

## Structure

1. Title / filing reference
2. Company particulars
3. Event / transaction particulars
4. Board / shareholder approval details
5. Attached documents list, if supplied
6. Verification / signatory block
