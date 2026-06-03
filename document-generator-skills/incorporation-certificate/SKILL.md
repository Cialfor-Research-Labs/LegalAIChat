---
name: indian-company-certificate-generator
description: Generate a company incorporation certificate style draft or related corporate certificate from frontend inputs covering company name, CIN, date of incorporation, registered office, and certifying authority details.
---

# Company Incorporation / Corporate Certificate

Use this skill when `documentType` indicates certificate of incorporation, company certificate, corporate certificate, or a certificate-style company status document.

## Input mapping

- `partyDetails` -> company identity details
- `recipientDetails` -> requesting party or issuing authority context
- `caseDetails` -> certificate purpose, incorporation details, CIN, registered office, corporate status
- `relevantInfo` -> issuing authority wording, date, seal, reference numbers, legal basis

## Output rules

1. Draft only the certificate-style document text.
2. Do not invent CIN, incorporation dates, or government-issued identifiers.
3. Use placeholders for all official numbers and seals if missing.
4. Keep style formal, short, and certification-oriented.
5. Avoid converting the certificate into an agreement or pleading.

## Structure

1. Title
2. Issuing / certifying authority line, if supplied
3. Certification statement
4. Company particulars
5. Date and place
6. Signature / seal placeholders
