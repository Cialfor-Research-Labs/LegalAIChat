# Indian Legal Document Generator Skills

This folder contains drafting skills for the frontend `Document Generator` workflow only.

The current frontend input model is:

- `documentType`
- `partyDetails`
- `recipientDetails`
- `caseDetails`
- `relevantInfo`

These skills are written for Indian legal drafting and are intended to be wired to the backend later.

## Classification of the provided sample files

### Generator document types

- `C:\Users\ktv02\Downloads\Legal Documents\Plaint.pdf` → Civil plaint
- `C:\Users\ktv02\Downloads\Legal Documents\Written-Statement-DU.pdf` → Written statement
- `C:\Users\ktv02\Downloads\Legal Documents\format-for-affidavit.pdf` → Affidavit
- `C:\Users\ktv02\Downloads\Legal Documents\Form -III   Interlocutory Application.pdf` → Interlocutory application
- `C:\Users\ktv02\Downloads\Legal Documents\Vakalatnama form.pdf` → Vakalatnama
- `C:\Users\ktv02\Downloads\Legal Documents\Review-of-EWS-Judge-with-finding.pdf` → Review petition / review application
- `C:\Users\ktv02\Downloads\Legal Documents\writ-of-certiorari.pdf` → Writ petition for certiorari
- `C:\Users\ktv02\Downloads\Legal Documents\writ-of-habeas-corpus.pdf` → Writ petition for habeas corpus
- `C:\Users\ktv02\Downloads\Legal Documents\writ-of-mandamus.pdf` → Writ petition for mandamus
- `C:\Users\ktv02\Downloads\Legal Documents\writ-of-prohibition.pdf` → Writ petition for prohibition
- `C:\Users\ktv02\Downloads\Legal Documents\writ-of-quo-warranto.pdf` → Writ petition for quo warranto

### Additional generator document types from `part2`

- `C:\Users\ktv02\Downloads\Legal Documents\part2\convertible_note.pdf` → Convertible note
- `C:\Users\ktv02\Downloads\Legal Documents\part2\23-05-31-VC-Post-Money-Template-SAFE-1.pdf` → SAFE / Simple Agreement for Future Equity
- `C:\Users\ktv02\Downloads\Legal Documents\part2\Employment Agreement w ESOP.docx` → Employment agreement with ESOP
- `C:\Users\ktv02\Downloads\Legal Documents\part2\MCA-ROC-Filing.pdf` → MCA / ROC filing draft
- `C:\Users\ktv02\Downloads\Legal Documents\part2\0_0_91110123612221Companycertificate.pdf` → Company incorporation / corporate certificate
- `C:\Users\ktv02\Downloads\Legal Documents\part2\share-transfer-agreement.pdf` → Share transfer agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\M&A_SampleC-e.pdf` → M&A / acquisition agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\0_0_411112171281MOA.pdf` → Memorandum of Association
- `C:\Users\ktv02\Downloads\Legal Documents\part2\software-license-agreement.pdf` → Software license agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\Onestream-SaaS-Agreement.pdf` → SaaS agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\HPARC-software-development-agreement.pdf` → Software development agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\SUVIDHA FRANCHISE AGREEMENT_ACEUP Partnership.pdf` → Franchise agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\1655708276_rentalagreementsampleandallyouneedtoknow.pdf` → Rent agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\Lease Deed.pdf` → Lease deed
- `C:\Users\ktv02\Downloads\Legal Documents\part2\startup_founders_sha_sample.pdf` → Shareholders agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\5802627584JVAgreement.pdf` → Joint venture agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\Partnership deed.pdf` → Partnership deed
- `C:\Users\ktv02\Downloads\Legal Documents\part2\CONSULTANCY_AGREEMENT.pdf` → Consultancy agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\Vendor Agreement Template-02.2021_2.pdf` → Vendor agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\18_ Freelance Agreement.pdf` → Freelance agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\EMPLOYMENT-AGREEMENT.pdf` → Employment agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\Independent-Contractor_Freelancer.pdf` → Independent contractor agreement
- `C:\Users\ktv02\Downloads\Legal Documents\part2\MoU Format.pdf` → Memorandum of Understanding
- `C:\Users\ktv02\Downloads\Legal Documents\part2\PensionRevision-ContemptPetition-150424s.pdf` → Contempt petition
- `C:\Users\ktv02\Downloads\Legal Documents\part2\EVIDENCE BY WAY OF AFFIDAVIT IN A SUIT FOR RECOVERY.pdf` → Evidence by way of affidavit
- `C:\Users\ktv02\Downloads\Legal Documents\part2\notice-reply.pdf` → Reply to legal notice
- `C:\Users\ktv02\Downloads\Legal Documents\part2\Anticipatory-Bail-Application-by-Accused.pdf` → Anticipatory bail application

### Reference-only materials

- `C:\Users\ktv02\Downloads\Legal Documents\WOMENS-VOICE-VS-State-OF-KARNATAKA.pdf` → Reported judgment / precedent reference
- `C:\Users\ktv02\Downloads\Legal Documents\17921_0.pdf` → Order / judgment record reference
- `C:\Users\ktv02\Downloads\Legal Documents\787548_1608480481.docx` → Drafting sample reference
- `C:\Users\ktv02\Downloads\Legal Documents\part2\01-legal_notice_facebook.pdf` → Legal notice sample reference for the dedicated legal notice generator
- `C:\Users\ktv02\Downloads\Legal Documents\part2\PBose_WPC_1512_2019_redacted.pdf` → Writ petition precedent reference

### Ambiguous filename-only references

These were not modeled as standalone generator types because the filenames alone do not reliably identify the document genre:

- `C:\Users\ktv02\Downloads\Legal Documents\part2\1632984644.pdf`
- `C:\Users\ktv02\Downloads\Legal Documents\part2\1714631710.pdf`
- `C:\Users\ktv02\Downloads\Legal Documents\part2\2025011058-1.pdf`
- `C:\Users\ktv02\Downloads\Legal Documents\part2\2026031120.pdf`
- `C:\Users\ktv02\Downloads\Legal Documents\part2\8077390661608748951sc10c.pdf`
- `C:\Users\ktv02\Downloads\Legal Documents\part2\corg_ex6z4.pdf`
- `C:\Users\ktv02\Downloads\Legal Documents\part2\FORM IF 1.pdf`
- `C:\Users\ktv02\Downloads\Legal Documents\part2\MM030_Applicant_Seifeslam-Dleiow.pdf`

These reference-only files are useful as style or precedent material, but they are not modeled here as standalone generator document types.

## Skill folders

- `document-generator-skills/plaint/SKILL.md`
- `document-generator-skills/written-statement/SKILL.md`
- `document-generator-skills/affidavit/SKILL.md`
- `document-generator-skills/interlocutory-application/SKILL.md`
- `document-generator-skills/vakalatnama/SKILL.md`
- `document-generator-skills/review-petition/SKILL.md`
- `document-generator-skills/writ-certiorari/SKILL.md`
- `document-generator-skills/writ-habeas-corpus/SKILL.md`
- `document-generator-skills/writ-mandamus/SKILL.md`
- `document-generator-skills/writ-prohibition/SKILL.md`
- `document-generator-skills/writ-quo-warranto/SKILL.md`
- `document-generator-skills/convertible-note/SKILL.md`
- `document-generator-skills/safe-note/SKILL.md`
- `document-generator-skills/incorporation-certificate/SKILL.md`
- `document-generator-skills/mca-roc-filing/SKILL.md`
- `document-generator-skills/share-transfer-agreement/SKILL.md`
- `document-generator-skills/ma-agreement/SKILL.md`
- `document-generator-skills/moa/SKILL.md`
- `document-generator-skills/software-license-agreement/SKILL.md`
- `document-generator-skills/saas-agreement/SKILL.md`
- `document-generator-skills/software-development-agreement/SKILL.md`
- `document-generator-skills/franchise-agreement/SKILL.md`
- `document-generator-skills/rent-agreement/SKILL.md`
- `document-generator-skills/lease-deed/SKILL.md`
- `document-generator-skills/shareholders-agreement/SKILL.md`
- `document-generator-skills/joint-venture-agreement/SKILL.md`
- `document-generator-skills/partnership-deed/SKILL.md`
- `document-generator-skills/consultancy-agreement/SKILL.md`
- `document-generator-skills/vendor-agreement/SKILL.md`
- `document-generator-skills/freelance-agreement/SKILL.md`
- `document-generator-skills/employment-agreement/SKILL.md`
- `document-generator-skills/employment-agreement-esop/SKILL.md`
- `document-generator-skills/independent-contractor-agreement/SKILL.md`
- `document-generator-skills/mou/SKILL.md`
- `document-generator-skills/contempt-petition/SKILL.md`
- `document-generator-skills/evidence-affidavit/SKILL.md`
- `document-generator-skills/notice-reply/SKILL.md`
- `document-generator-skills/anticipatory-bail-application/SKILL.md`
