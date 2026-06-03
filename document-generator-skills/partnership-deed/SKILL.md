---
name: indian-partnership-deed-generator
description: Generate a partnership deed from frontend inputs covering partners, capital contribution, profit sharing, management, duties, banking, retirement, and dissolution.
---

# Partnership Deed

Use this skill when `documentType` indicates partnership deed, firm partnership agreement, or business partnership formation document.

## Input mapping

- `partyDetails` -> partner details
- `recipientDetails` -> additional partners or confirming parties
- `caseDetails` -> firm name, business, capital, profit sharing, duties, accounts, authority
- `relevantInfo` -> remuneration, banking, retirement, admission, dissolution, arbitration

## Output rules

1. Draft only the deed.
2. Do not invent partner shares, capital, or registration details.
3. Use placeholders where firm particulars are missing.
4. Keep it firm-law and business-operations oriented.
5. Mention Indian partnership context, but avoid unsupported statutory detail.

## Structure

1. Parties and business name
2. Place of business and commencement
3. Capital contribution
4. Profit and loss sharing
5. Duties and authority of partners
6. Accounts, banking, drawings
7. Admission / retirement / death / dissolution
8. Dispute resolution and signatures
