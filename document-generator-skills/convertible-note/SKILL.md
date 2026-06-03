---
name: indian-convertible-note-generator
description: Generate an Indian-law convertible note or convertible debt instrument from frontend inputs covering investor, company, amount, conversion, valuation, maturity, interest, and default mechanics.
---

# Indian Convertible Note

Use this skill when `documentType` indicates a convertible note, convertible debt, startup convertible instrument, or bridge financing note.

## Input mapping

- `partyDetails` -> company and investor details
- `recipientDetails` -> counterparty or additional obligor details
- `caseDetails` -> investment amount, tranche, conversion trigger, maturity, interest, valuation terms
- `relevantInfo` -> cap table notes, security, conditions precedent, governing law, notices, annexures

## Output rules

1. Draft only the instrument text.
2. Use Indian commercial and startup-financing context.
3. Do not invent pricing, valuation caps, discounts, maturity periods, or regulatory compliance facts.
4. Use placeholders for missing commercial terms.
5. Keep clause numbering clean and investor-document style professional.

## Structure

1. Title and date
2. Parties
3. Background / recitals
4. Subscription amount and issuance
5. Conversion mechanics
6. Valuation cap / discount / qualified financing triggers
7. Interest and maturity, if applicable
8. Representations and covenants
9. Events of default / repayment mechanics, if applicable
10. Confidentiality, notices, governing law, dispute resolution
11. Signature blocks
