---
name: indian-employment-esop-agreement-generator
description: Generate an employment agreement with ESOP-related provisions from frontend inputs covering role, salary, equity or ESOP grant references, vesting, confidentiality, and termination.
---

# Employment Agreement with ESOP

Use this skill when `documentType` indicates employment agreement with ESOP, startup employment plus stock options, or executive employment with equity incentives.

## Input mapping

- `partyDetails` -> employer and employee details
- `recipientDetails` -> plan administrator, parent company, or affiliate details if relevant
- `caseDetails` -> role, compensation, ESOP / option references, vesting, cliffs, termination treatment
- `relevantInfo` -> plan rules, acceleration, confidentiality, IP, notice period, policies

## Output rules

1. Draft only the employment document.
2. Do not invent option counts, exercise price, or vesting schedules.
3. Use placeholders where ESOP terms are incomplete.
4. Keep ESOP clauses tied to the broader plan where appropriate.
5. Avoid implying grant effectiveness if board or plan approval is not stated.

## Structure

1. Employment terms
2. Compensation and benefits
3. ESOP / option grant reference
4. Vesting and plan-governed clauses
5. Confidentiality, IP, restrictions
6. Notice and termination
7. Signatures
