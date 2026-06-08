export type DocumentFieldType = 'text' | 'textarea' | 'date' | 'number' | 'select';

export interface DocumentFieldOption {
  label: string;
  value: string;
}

export interface DocumentFieldSchema {
  key: string;
  label: string;
  type: DocumentFieldType;
  required?: boolean;
  placeholder?: string;
  options?: DocumentFieldOption[];
  rows?: number;
}

export interface DocumentFieldGroup {
  key: string;
  title: string;
  fields: DocumentFieldSchema[];
}

const text = (
  key: string,
  label: string,
  placeholder: string,
  required = false,
): DocumentFieldSchema => ({ key, label, type: 'text', placeholder, required });

const textarea = (
  key: string,
  label: string,
  placeholder: string,
  required = false,
  rows = 4,
): DocumentFieldSchema => ({ key, label, type: 'textarea', placeholder, required, rows });

const date = (key: string, label: string, required = false): DocumentFieldSchema => ({
  key,
  label,
  type: 'date',
  required,
});

const number = (
  key: string,
  label: string,
  placeholder: string,
  required = false,
): DocumentFieldSchema => ({ key, label, type: 'number', placeholder, required });

const select = (
  key: string,
  label: string,
  options: DocumentFieldOption[],
  required = false,
): DocumentFieldSchema => ({ key, label, type: 'select', options, required });

const partyGroup = (...fields: DocumentFieldSchema[]): DocumentFieldGroup => ({
  key: 'party-details',
  title: 'Party Details',
  fields,
});

const counterpartyGroup = (...fields: DocumentFieldSchema[]): DocumentFieldGroup => ({
  key: 'recipient-details',
  title: 'Other Party Details',
  fields,
});

const courtGroup = (...fields: DocumentFieldSchema[]): DocumentFieldGroup => ({
  key: 'court-proceeding-details',
  title: 'Court / Proceeding Details',
  fields,
});

const matterGroup = (...fields: DocumentFieldSchema[]): DocumentFieldGroup => ({
  key: 'matter-details',
  title: 'Matter Details',
  fields,
});

const financeGroup = (...fields: DocumentFieldSchema[]): DocumentFieldGroup => ({
  key: 'financial-terms',
  title: 'Financial Terms',
  fields,
});

const propertyGroup = (...fields: DocumentFieldSchema[]): DocumentFieldGroup => ({
  key: 'property-details',
  title: 'Property Details',
  fields,
});

const signatureGroup = (...fields: DocumentFieldSchema[]): DocumentFieldGroup => ({
  key: 'signatures-witnesses',
  title: 'Signatures / Witnesses',
  fields,
});

const documentNature = [
  { label: 'Civil', value: 'civil' },
  { label: 'Criminal', value: 'criminal' },
  { label: 'Commercial', value: 'commercial' },
  { label: 'Corporate', value: 'corporate' },
  { label: 'Employment', value: 'employment' },
  { label: 'Property', value: 'property' },
  { label: 'Technology', value: 'technology' },
];

export const plaintFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('plaintiff_name', 'Plaintiff Name', 'Full name of the plaintiff', true),
    textarea('plaintiff_address', 'Plaintiff Address', 'Residential or business address', true),
    text('plaintiff_description', 'Plaintiff Description', 'Occupation, entity type, or role'),
  ),
  counterpartyGroup(
    text('defendant_name', 'Defendant Name', 'Full name of the defendant', true),
    textarea('defendant_address', 'Defendant Address', 'Residential or business address', true),
    text('defendant_description', 'Defendant Description', 'Occupation, designation, or entity type'),
  ),
  courtGroup(
    text('court_name', 'Court / Forum', 'Name of the court', true),
    text('jurisdiction_place', 'Jurisdiction Place', 'City / district / state', true),
    number('claim_value', 'Suit Valuation / Claim Amount', 'Value if known'),
  ),
  matterGroup(
    textarea('cause_of_action', 'Cause of Action', 'What happened and why the suit is filed', true, 5),
    textarea('material_facts', 'Material Facts', 'Chronological facts', true, 6),
    textarea('reliefs_sought', 'Reliefs Sought', 'Exact prayers against the defendant', true, 4),
  ),
];

export const writtenStatementFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('defendant_name', 'Defendant Name', 'Full name of the defendant', true),
    textarea('defendant_address', 'Defendant Address', 'Address of the defendant', true),
  ),
  counterpartyGroup(
    text('plaintiff_name', 'Plaintiff Name', 'Full name of the plaintiff', true),
    textarea('plaintiff_address', 'Plaintiff Address', 'Address of the plaintiff'),
  ),
  courtGroup(
    text('court_name', 'Court / Forum', 'Name of the court', true),
    text('case_number', 'Case Number', 'Suit number if available'),
  ),
  matterGroup(
    textarea('plaint_summary', 'Plaint Summary', 'Main allegations to respond to', true, 5),
    textarea('defence_summary', 'Defence Summary', 'Defendant version and objections', true, 6),
    textarea('prayer', 'Prayer', 'How the suit should be disposed of', true, 3),
  ),
];

export const affidavitFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('deponent_name', 'Deponent Name', 'Full name of deponent', true),
    text('deponent_relation', 'Father / Spouse Name', 'S/o, D/o, W/o details'),
    textarea('deponent_address', 'Deponent Address', 'Address of deponent', true),
  ),
  courtGroup(
    text('forum_name', 'Court / Forum', 'Forum where affidavit is used'),
    text('case_title', 'Case Title', 'Matter title'),
    text('case_number', 'Case Number', 'Case / petition number'),
  ),
  matterGroup(
    textarea('affirmed_facts', 'Affirmed Facts', 'Facts being sworn / affirmed', true, 6),
    textarea('document_references', 'Document References', 'Annexures, exhibits, or supporting records'),
  ),
  signatureGroup(
    text('place_of_execution', 'Place', 'Place of signing'),
    date('date_of_execution', 'Date of Execution'),
    text('attesting_authority', 'Notary / Oath Authority', 'Name/designation if known'),
  ),
];

export const interlocutoryApplicationFieldGroups: DocumentFieldGroup[] = [
  partyGroup(text('applicant_name', 'Applicant Name', 'Applicant / petitioner name', true)),
  counterpartyGroup(text('respondent_name', 'Respondent Name', 'Respondent name', true)),
  courtGroup(
    text('court_name', 'Court / Forum', 'Name of court or authority', true),
    text('main_case_number', 'Main Case Number', 'Pending case reference', true),
  ),
  matterGroup(
    text('application_type', 'Application Type', 'Stay, exemption, amendment, impleadment, etc.', true),
    textarea('grounds', 'Grounds', 'Why interim relief is needed', true, 5),
    textarea('prayer', 'Prayer', 'Exact interim relief sought', true, 3),
  ),
];

export const vakalatnamaFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('executant_name', 'Client / Executant Name', 'Name of client', true),
    textarea('executant_address', 'Client Address', 'Residential address', true),
    text('client_contact', 'Client Contact', 'Phone or email'),
  ),
  courtGroup(
    text('matter_title', 'Matter Title', 'Case title / subject matter', true),
    text('forum_name', 'Court / Forum', 'Court / tribunal / authority', true),
  ),
  counterpartyGroup(text('opposite_party_name', 'Opposite Party', 'Opposite party name or title')),
  signatureGroup(
    text('advocate_name', 'Advocate Name', 'Name of advocate', true),
    text('advocate_enrolment', 'Enrollment Number', 'Bar enrollment number'),
    text('witness_names', 'Witness Names', 'Names of witnesses if known'),
  ),
];

export const reviewPetitionFieldGroups: DocumentFieldGroup[] = [
  partyGroup(text('review_petitioner', 'Review Petitioner', 'Applicant / petitioner name', true)),
  counterpartyGroup(text('respondent_name', 'Respondent', 'Respondent name')),
  courtGroup(
    text('forum_name', 'Court / Forum', 'Same forum that passed the order', true),
    text('impugned_case_number', 'Original Case Number', 'Case number of impugned order', true),
    date('impugned_order_date', 'Impugned Order Date'),
  ),
  matterGroup(
    textarea('error_apparent', 'Error / Review Ground', 'Error apparent or new matter', true, 5),
    textarea('relief_sought', 'Relief Sought', 'Review, recall, modify, rehear', true, 3),
  ),
];

export const writFieldGroups: DocumentFieldGroup[] = [
  partyGroup(text('petitioner_name', 'Petitioner Name', 'Petitioner name', true)),
  counterpartyGroup(text('respondent_authority', 'Respondent Authority', 'Authority / state / respondent', true)),
  courtGroup(
    text('high_court_name', 'Court', 'High Court / Supreme Court', true),
    text('territorial_jurisdiction', 'Territorial Jurisdiction', 'State / bench / place'),
  ),
  matterGroup(
    select('writ_nature', 'Nature', documentNature),
    textarea('challenge_or_grievance', 'Challenge / Grievance', 'Impugned action or grievance', true, 5),
    textarea('relief_sought', 'Relief Sought', 'Quashing / direction / production / restraint', true, 3),
  ),
];

export const contemptPetitionFieldGroups: DocumentFieldGroup[] = [
  partyGroup(text('petitioner_name', 'Petitioner Name', 'Name of petitioner', true)),
  counterpartyGroup(text('contemnor_name', 'Contemnor / Respondent', 'Name of alleged contemnor', true)),
  courtGroup(
    text('court_name', 'Court', 'Court that passed the order', true),
    text('original_case_number', 'Original Case Number', 'Prior case reference', true),
    date('order_date', 'Order Date'),
  ),
  matterGroup(
    textarea('order_terms', 'Order Terms', 'What the prior order directed', true, 4),
    textarea('disobedience_details', 'Disobedience Details', 'How the order was violated', true, 5),
    textarea('relief_sought', 'Relief Sought', 'Contempt relief and compliance prayer', true, 3),
  ),
];

export const evidenceAffidavitFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('witness_name', 'Witness / Deponent Name', 'Name of witness', true),
    textarea('witness_address', 'Witness Address', 'Address', true),
  ),
  courtGroup(
    text('court_name', 'Court', 'Court name', true),
    text('case_number', 'Case Number', 'Suit / matter number'),
  ),
  matterGroup(
    textarea('testimony_summary', 'Testimony Summary', 'Evidence in chief', true, 6),
    textarea('exhibit_details', 'Exhibit Details', 'Documents / exhibits relied on'),
  ),
];

export const anticipatoryBailFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('applicant_name', 'Applicant Name', 'Name of accused / applicant', true),
    textarea('applicant_address', 'Applicant Address', 'Address', true),
  ),
  counterpartyGroup(
    text('police_station', 'Police Station', 'Police station name', true),
    text('state_name', 'State / Agency', 'State / agency / complainant'),
  ),
  courtGroup(
    text('court_name', 'Court', 'Sessions Court / High Court', true),
    text('fir_number', 'FIR / Complaint Number', 'FIR number if known'),
    date('fir_date', 'FIR Date'),
  ),
  matterGroup(
    textarea('allegations', 'Allegations', 'Brief allegations and background', true, 5),
    textarea('grounds_for_bail', 'Grounds for Anticipatory Bail', 'Why protection should be granted', true, 5),
  ),
];

export const noticeReplyFieldGroups: DocumentFieldGroup[] = [
  partyGroup(text('replying_party', 'Replying Party', 'Person / entity replying', true)),
  counterpartyGroup(text('notice_sender', 'Original Notice Sender', 'Sender / advocate / claimant', true)),
  matterGroup(
    textarea('notice_allegations', 'Notice Allegations', 'What the original notice alleges', true, 5),
    textarea('reply_position', 'Reply Position', 'Denials, admissions, and defence', true, 6),
    textarea('reply_demands', 'Reply / Closing Demands', 'What relief or closure is sought', true, 3),
  ),
];

export const propertyAgreementFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('owner_name', 'Owner / Lessor Name', 'Landlord / lessor name', true),
    textarea('owner_address', 'Owner Address', 'Address of owner / lessor', true),
  ),
  counterpartyGroup(
    text('occupant_name', 'Tenant / Lessee Name', 'Tenant / lessee name', true),
    textarea('occupant_address', 'Tenant / Lessee Address', 'Address of tenant / lessee', true),
  ),
  propertyGroup(
    textarea('property_address', 'Property Address', 'Full property address', true),
    select('property_type', 'Property Type', [
      { label: 'Residential', value: 'residential' },
      { label: 'Commercial', value: 'commercial' },
      { label: 'Industrial', value: 'industrial' },
    ]),
    text('permitted_use', 'Permitted Use', 'Residential, office, warehouse, etc.'),
  ),
  financeGroup(
    number('rent_amount', 'Rent / Lease Amount', 'Monthly or periodic rent', true),
    number('security_deposit', 'Security Deposit', 'Security deposit amount'),
    date('start_date', 'Start Date', true),
    date('end_date', 'End Date', true),
  ),
];

export const employmentAgreementFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('employer_name', 'Employer Name', 'Company / employer name', true),
    textarea('employer_address', 'Employer Address', 'Registered / office address', true),
  ),
  counterpartyGroup(
    text('employee_name', 'Employee Name', 'Employee full name', true),
    textarea('employee_address', 'Employee Address', 'Residential address', true),
  ),
  matterGroup(
    text('designation', 'Designation', 'Job title', true),
    date('joining_date', 'Joining Date'),
    text('work_location', 'Work Location', 'Office / remote / hybrid'),
    textarea('duties', 'Duties / Role Summary', 'Main responsibilities', true, 4),
  ),
  financeGroup(
    number('salary', 'Compensation', 'Monthly / annual compensation', true),
    text('probation', 'Probation Period', 'If applicable'),
    text('notice_period', 'Notice Period', 'Notice period on termination'),
  ),
];

export const employmentEsopFieldGroups: DocumentFieldGroup[] = [
  ...employmentAgreementFieldGroups,
  financeGroup(
    text('esop_plan_name', 'ESOP Plan / Grant Reference', 'Plan or grant name'),
    text('option_count', 'Option Count', 'Number of options if known'),
    text('vesting_schedule', 'Vesting Schedule', 'Cliff / vesting details'),
  ),
];

export const servicesAgreementFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('client_name', 'Client Name', 'Client / customer name', true),
    textarea('client_address', 'Client Address', 'Office address', true),
  ),
  counterpartyGroup(
    text('service_provider_name', 'Service Provider', 'Vendor / consultant / contractor name', true),
    textarea('service_provider_address', 'Service Provider Address', 'Office / residential address', true),
  ),
  matterGroup(
    textarea('scope_of_services', 'Scope of Services', 'Services / deliverables', true, 5),
    date('start_date', 'Start Date', true),
    date('end_date', 'End Date', true),
    text('deliverable_timeline', 'Timeline / Milestones', 'Delivery schedule'),
  ),
  financeGroup(
    number('fee_amount', 'Fees / Charges', 'Commercial value', true),
    text('payment_terms', 'Payment Terms', 'Invoices, milestones, due dates', true),
  ),
];

export const softwareLicenseFieldGroups: DocumentFieldGroup[] = [
  ...servicesAgreementFieldGroups,
  matterGroup(
    text('software_name', 'Software / Product Name', 'Licensed software', true),
    text('license_scope', 'License Scope', 'Users, seats, modules, territory', true),
    textarea('usage_restrictions', 'Usage Restrictions', 'Restrictions on use, reverse engineering, sublicensing'),
  ),
];

export const saasFieldGroups: DocumentFieldGroup[] = [
  ...servicesAgreementFieldGroups,
  matterGroup(
    text('platform_name', 'Platform / Service Name', 'Name of SaaS service', true),
    text('subscription_plan', 'Subscription Plan', 'Plan / package / user base'),
    textarea('service_levels', 'Service / Support Levels', 'Uptime, support response, maintenance'),
  ),
];

export const corporateTransactionFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('company_name', 'Company / Target Name', 'Company or target name', true),
    textarea('company_address', 'Company Address', 'Registered office'),
  ),
  counterpartyGroup(
    text('counterparty_name', 'Investor / Buyer / Transferor / Shareholder', 'Other principal party', true),
    textarea('counterparty_address', 'Counterparty Address', 'Address of counterparty'),
  ),
  matterGroup(
    text('transaction_type', 'Transaction Type', 'Investment, transfer, acquisition, governance', true),
    textarea('transaction_summary', 'Transaction Summary', 'What the transaction/document covers', true, 5),
  ),
  financeGroup(
    number('transaction_value', 'Consideration / Investment Amount', 'Amount if known'),
    text('equity_details', 'Shares / Equity Details', 'Class, number, cap, discount, etc.'),
  ),
];

export const moaFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('company_name', 'Proposed / Company Name', 'Name of company', true),
    text('registered_office_state', 'Registered Office State', 'State of registered office', true),
  ),
  matterGroup(
    textarea('main_objects', 'Main Objects', 'Principal objects clause', true, 5),
    textarea('incidental_objects', 'Incidental Objects', 'Incidental / ancillary objects'),
    text('liability_clause', 'Liability Clause', 'Limited by shares / guarantee'),
  ),
  financeGroup(number('authorised_capital', 'Authorised Capital', 'Authorised share capital')),
  signatureGroup(text('subscriber_details', 'Subscriber Details', 'Subscribers and witness details')),
];

export const companyCertificateFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('company_name', 'Company Name', 'Company / entity name', true),
    text('cin', 'CIN / Registration Number', 'CIN / incorporation number'),
    date('incorporation_date', 'Incorporation Date'),
  ),
  matterGroup(
    text('certificate_purpose', 'Certificate Purpose', 'What the certificate certifies', true),
    textarea('status_details', 'Status / Particulars', 'Registered office, status, nature of certificate', true, 4),
  ),
  signatureGroup(text('issuing_authority', 'Issuing Authority', 'Authority / officer / certifier')),
];

export const mcaRocFieldGroups: DocumentFieldGroup[] = [
  partyGroup(
    text('company_name', 'Company Name', 'Company name', true),
    text('cin', 'CIN', 'Corporate identification number'),
  ),
  matterGroup(
    text('form_reference', 'Form / Filing Reference', 'MCA form or filing reference', true),
    textarea('filing_event', 'Filing Event', 'Corporate event or compliance action', true, 5),
    date('event_date', 'Event Date'),
  ),
  signatureGroup(text('authorised_signatory', 'Authorised Signatory', 'Signatory / designation')),
];

export const signaturesBasicFieldGroups: DocumentFieldGroup[] = [
  signatureGroup(
    text('signatory_name', 'Signatory Name', 'Name of signatory / executing party'),
    text('witness_details', 'Witness Details', 'Witness names if required'),
  ),
];
