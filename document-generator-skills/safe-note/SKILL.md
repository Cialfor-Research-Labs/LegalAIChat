---
name: indian-safe-generator
description: Generate a startup SAFE-style investment instrument adapted for Indian commercial use from frontend inputs covering investor, company, amount, valuation cap, discount, and conversion events.
---

# SAFE / Simple Agreement for Future Equity

Use this skill when `documentType` indicates a SAFE, future equity instrument, post-money SAFE, or early-stage equity financing agreement.

## Input mapping

- `partyDetails` -> company and investor details
- `recipientDetails` -> additional founders or related parties if relevant
- `caseDetails` -> purchase amount, valuation cap, discount, equity financing triggers, liquidity and dissolution treatment
- `relevantInfo` -> board approvals, cap table notes, governing law, reserved matters, compliance notes

## Output rules

1. Draft only the SAFE instrument.
2. Keep the document concise and transaction-oriented.
3. Do not invent cap tables, share prices, or regulatory approvals.
4. Use placeholders where economics are incomplete.
5. Preserve startup finance terminology while keeping Indian-law references neutral unless supplied.

## Structure

1. Title and date
2. Parties
3. Purchase amount
4. Conversion events
5. Valuation cap / discount, if applicable
6. Liquidity / dissolution provisions
7. Representations
8. Miscellaneous clauses
9. Signature blocks
