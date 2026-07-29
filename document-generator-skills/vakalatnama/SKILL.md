---
name: indian-vakalatnama-generator
description: Generate a vakalatnama format for Indian litigation matching the exact form template from Vakalatnama form.pdf with precise dotted lines, bold VERSUS, exact legal clauses, and signature layout.
---

# Indian Vakalatnama

Use this skill when `documentType` indicates vakalatnama, memo of appearance authority, or authorization of advocate in an Indian court or tribunal matter.

## Input mapping

- `partyDetails` / `executant_name` → client / executant details & address
- `recipientDetails` / `opposite_party_name` → defendant(s) / respondent(s) / accused name
- `caseDetails` / `forum_name` / `case_number` / `jurisdiction_year` → court name, suit/appeal number, jurisdiction/year
- `relevantInfo` / `advocate_name` / `advocate_enrolment` / `execution_date` → advocate details, enrollment number, signing date

## Output rules

1. Output ONLY the Vakalatnama text directly. Do NOT wrap in markdown code blocks (` ``` `) or markdown table borders (`|`).
2. **VERSUS** MUST be bold (`**VERSUS**`).
3. Format filled values inside dotted lines (`..................................................................`) so the output looks like an authentic court form.
4. Keep exact legal wording, paragraph indents, and signature positions.

## Format Template

IN THE COURT OF {forum_name}....................................................................................................
Suit/Appeal No. {case_number}........................................................................JURISDICTION OF {jurisdiction_year}
In re:-
{executant_name}.......................................................................... Plaintiff(s) or Petitioner(s)
                                                                           Appellant(s) Complainant(s)

**VERSUS**

{opposite_party_name}..................................................................... Defendant (s)/ Respondent(s) / Accused Know all to whom
these Present shall come that I/we {executant_name}, {executant_address}..........................................................
...................................................................................................................................
The above named {executant_name}...................................................................................................
................................................................................................... do hereby appoint
{advocate_name}, Enrollment No. {advocate_enrolment}................................................................................
(herein after called the advocate/s) to be my / our Advocate in the above – noted case authorize him:-

        To act, appear and plead in the above-noted case in this court or in any other court in which the same may be tried or heard and also in the appellate court including High Court subject to payment of fees separately for each court by me/us.

        To sign file, verify and present pleadings, appeals cross-objection or petitions for executions review, revision, withdrawal, compromise or other petitions or affidavits or other documents as may be deemed necessary or proper for the prosecution of the said case in all its stages subjects to payment of fees for each stage.

        To file and take back documents, to admit and/or deny the documents of opposite party.

        To withdraw or compromise the said case or submit to arbitration any differences of disputes that may arise touching or in any manner relating to the said case.

        To take execution proceedings on paying separate fee.

        To deposit, draw and receive money, cheques, cash and grant receipts hereof and to do all other acts and things which may be necessary to be done for the progress and in the course of the prosecution on the said case.

        To appoint and instruct any other Legal Practitioner authorizing him to exercise the power and authority hereby conferred upon the Advocate whenever he may think fit to do so and to sign the power of attorney on our behalf.

        And I/we undersigned to hereby agree to ratify and confirm all acts done by the Advocate or his substitute in the matter as my/our own acts, as if done by me/us to all intents and purpose.

        And I/we undertake that I/We or my/our duly authorized agent would appear in court on all hearings and will inform the Advocate for appearance when the case is called.

        And I/We undersigned do hereby agree not to hold the advocate or his substitute responsible for the result of the said case. The adjournment costs whenever ordered by the court shall be of the Advocate which he shall receive and retain for himself.

        And I/we undersigned do hereby agree that in the event of the whole or part of the fee agreed by me/us to be paid to the advocate remaining unpaid he shall be entitled to withdraw from the prosecution of the said case until the same is paid up. The fee settle is only for the above case and above Court. I/We hereby agree that once the fee is paid, I /We will not be entitled for the refund of the same in any case whatsoever and if the case prolongs for more than 3 years the original fee shall be paid again by me/us.

IN WITNESS WHERE OF I/We do hereunto set my/our hand to these presents the contents of which have been understood by me/us on this {execution_date} Accepted subject to the terms of the fees.


Advocate                                                Client                                                Client


I Identify the Signature/Thumb Impression of Below Mentioned Person,

Signed in My Presence. The Client.


