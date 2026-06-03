---
name: indian-employment-agreement-generator
description: Generate an employment agreement from frontend inputs covering role, compensation, term, duties, confidentiality, IP, termination, and policy compliance.
---

# Employment Agreement

Use this skill when `documentType` indicates employment agreement, appointment letter style employment contract, or employer-employee service agreement.

## Input mapping

- `partyDetails` -> employer and employee details
- `recipientDetails` -> reporting manager or affiliate details if relevant
- `caseDetails` -> designation, start date, compensation, probation, duties, work location, benefits
- `relevantInfo` -> leave, confidentiality, IP, restrictive covenants, termination, notice period, policies

## Output rules

1. Draft only the employment agreement.
2. Do not invent salary, role, or statutory benefit figures.
3. Use placeholders for missing compensation and policy details.
4. Keep employer obligations and employee duties balanced.
5. Use Indian employment context without overclaiming statutory compliance.

## Structure

1. Parties and appointment clause
2. Position and duties
3. Compensation and benefits
4. Probation / work conditions
5. Confidentiality, IP, conduct
6. Leave, notice, termination
7. General clauses and signatures
