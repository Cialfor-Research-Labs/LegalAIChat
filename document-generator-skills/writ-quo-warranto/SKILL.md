---
name: indian-writ-quo-warranto-generator
description: Generate a writ petition for quo warranto in Indian public law from frontend inputs alleging unlawful occupation of a public office, lack of eligibility, or invalid appointment.
---

# Writ Petition for Quo Warranto

Use this skill when `documentType` indicates writ of quo warranto or a petition questioning the legal authority by which a person holds a public office.

## Input mapping

- `partyDetails` → petitioner details
- `recipientDetails` → office-holder, appointing authority, and related respondents
- `caseDetails` → office in question, appointment facts, alleged disqualification or ineligibility, public law basis
- `relevantInfo` → notification details, eligibility criteria, appointment order, public office details, annexures

## Output rules

1. Draft only the writ petition.
2. Keep focus on public office and legal eligibility.
3. Do not invent service rules, qualifications, or appointment defects.
4. Use placeholders where notification numbers, rule names, or dates are absent.
5. Maintain a restrained public-law tone.

## Structure

1. Court heading
2. Cause title
3. Statement identifying the office and impugned appointment
4. Facts
5. Eligibility or legality challenge
6. Grounds
7. Prayer calling upon respondents to show authority and for declaration if appointment is invalid
8. Verification

## Drafting guidance

- Quo warranto is not for private service disputes alone; keep the public office element central.
- Explain the source of alleged ineligibility clearly.
- Relief should target the legality of holding office, not collateral grievances.

## Frontend generation note

The preview should read as a constitutional challenge to occupation of office and remain concise for later backend enrichment.
