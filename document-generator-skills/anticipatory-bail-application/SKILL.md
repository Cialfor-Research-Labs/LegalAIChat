---
name: indian-anticipatory-bail-generator
description: Generate an anticipatory bail application from frontend inputs covering accused details, FIR or apprehension facts, grounds for protection, cooperation, and prayer.
---

# Anticipatory Bail Application

Use this skill when `documentType` indicates anticipatory bail, pre-arrest bail application, or Section 438-style protection request.

## Input mapping

- `partyDetails` -> applicant / accused details
- `recipientDetails` -> state, complainant, police station, investigating agency details
- `caseDetails` -> FIR facts or apprehended arrest, allegations, applicant defence, cooperation, urgency
- `relevantInfo` -> offence sections if supplied, prior history, parity, medical issues, interim relief request

## Output rules

1. Draft only the bail application.
2. Do not invent FIR numbers, sections, or factual innocence claims.
3. Use placeholders where criminal case particulars are missing.
4. Keep tone respectful, cautious, and protection-oriented.
5. Avoid unsupported arguments on merits.

## Structure

1. Court heading
2. Bail application title
3. Applicant and respondent details
4. Facts and apprehension of arrest
5. Grounds for anticipatory bail
6. Cooperation undertakings
7. Prayer
8. Verification
