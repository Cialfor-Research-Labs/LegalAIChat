import affidavitSkill from '../../document-generator-skills/affidavit/SKILL.md?raw';
import anticipatoryBailApplicationSkill from '../../document-generator-skills/anticipatory-bail-application/SKILL.md?raw';
import consultancyAgreementSkill from '../../document-generator-skills/consultancy-agreement/SKILL.md?raw';
import contemptPetitionSkill from '../../document-generator-skills/contempt-petition/SKILL.md?raw';
import convertibleNoteSkill from '../../document-generator-skills/convertible-note/SKILL.md?raw';
import employmentAgreementSkill from '../../document-generator-skills/employment-agreement/SKILL.md?raw';
import employmentAgreementEsopSkill from '../../document-generator-skills/employment-agreement-esop/SKILL.md?raw';
import evidenceAffidavitSkill from '../../document-generator-skills/evidence-affidavit/SKILL.md?raw';
import franchiseAgreementSkill from '../../document-generator-skills/franchise-agreement/SKILL.md?raw';
import freelanceAgreementSkill from '../../document-generator-skills/freelance-agreement/SKILL.md?raw';
import incorporationCertificateSkill from '../../document-generator-skills/incorporation-certificate/SKILL.md?raw';
import independentContractorAgreementSkill from '../../document-generator-skills/independent-contractor-agreement/SKILL.md?raw';
import interlocutoryApplicationSkill from '../../document-generator-skills/interlocutory-application/SKILL.md?raw';
import jointVentureAgreementSkill from '../../document-generator-skills/joint-venture-agreement/SKILL.md?raw';
import leaseDeedSkill from '../../document-generator-skills/lease-deed/SKILL.md?raw';
import maAgreementSkill from '../../document-generator-skills/ma-agreement/SKILL.md?raw';
import mcaRocFilingSkill from '../../document-generator-skills/mca-roc-filing/SKILL.md?raw';
import moaSkill from '../../document-generator-skills/moa/SKILL.md?raw';
import mouSkill from '../../document-generator-skills/mou/SKILL.md?raw';
import noticeReplySkill from '../../document-generator-skills/notice-reply/SKILL.md?raw';
import partnershipDeedSkill from '../../document-generator-skills/partnership-deed/SKILL.md?raw';
import plaintSkill from '../../document-generator-skills/plaint/SKILL.md?raw';
import rentAgreementSkill from '../../document-generator-skills/rent-agreement/SKILL.md?raw';
import reviewPetitionSkill from '../../document-generator-skills/review-petition/SKILL.md?raw';
import safeNoteSkill from '../../document-generator-skills/safe-note/SKILL.md?raw';
import saasAgreementSkill from '../../document-generator-skills/saas-agreement/SKILL.md?raw';
import shareholdersAgreementSkill from '../../document-generator-skills/shareholders-agreement/SKILL.md?raw';
import shareTransferAgreementSkill from '../../document-generator-skills/share-transfer-agreement/SKILL.md?raw';
import softwareDevelopmentAgreementSkill from '../../document-generator-skills/software-development-agreement/SKILL.md?raw';
import softwareLicenseAgreementSkill from '../../document-generator-skills/software-license-agreement/SKILL.md?raw';
import vakalatnamaSkill from '../../document-generator-skills/vakalatnama/SKILL.md?raw';
import vendorAgreementSkill from '../../document-generator-skills/vendor-agreement/SKILL.md?raw';
import writCertiorariSkill from '../../document-generator-skills/writ-certiorari/SKILL.md?raw';
import writHabeasCorpusSkill from '../../document-generator-skills/writ-habeas-corpus/SKILL.md?raw';
import writMandamusSkill from '../../document-generator-skills/writ-mandamus/SKILL.md?raw';
import writProhibitionSkill from '../../document-generator-skills/writ-prohibition/SKILL.md?raw';
import writQuoWarrantoSkill from '../../document-generator-skills/writ-quo-warranto/SKILL.md?raw';
import writtenStatementSkill from '../../document-generator-skills/written-statement/SKILL.md?raw';
import {
  affidavitFieldGroups,
  anticipatoryBailFieldGroups,
  companyCertificateFieldGroups,
  contemptPetitionFieldGroups,
  corporateTransactionFieldGroups,
  employmentAgreementFieldGroups,
  employmentEsopFieldGroups,
  evidenceAffidavitFieldGroups,
  interlocutoryApplicationFieldGroups,
  mcaRocFieldGroups,
  moaFieldGroups,
  noticeReplyFieldGroups,
  plaintFieldGroups,
  propertyAgreementFieldGroups,
  reviewPetitionFieldGroups,
  saasFieldGroups,
  servicesAgreementFieldGroups,
  softwareLicenseFieldGroups,
  vakalatnamaFieldGroups,
  writFieldGroups,
  writtenStatementFieldGroups,
  type DocumentFieldGroup,
} from './documentFieldSchemas';

export interface DocumentSkillDefinition {
  value: string;
  label: string;
  skillName: string;
  skillContent: string;
  fieldGroups: DocumentFieldGroup[];
}

export const DOCUMENT_SKILLS: DocumentSkillDefinition[] = [
  { value: 'plaint', label: 'Civil Plaint', skillName: 'indian-plaint-generator', skillContent: plaintSkill, fieldGroups: plaintFieldGroups },
  { value: 'written-statement', label: 'Written Statement', skillName: 'indian-written-statement-generator', skillContent: writtenStatementSkill, fieldGroups: writtenStatementFieldGroups },
  { value: 'affidavit', label: 'Affidavit', skillName: 'indian-affidavit-generator', skillContent: affidavitSkill, fieldGroups: affidavitFieldGroups },
  { value: 'interlocutory-application', label: 'Interlocutory Application', skillName: 'indian-interlocutory-application-generator', skillContent: interlocutoryApplicationSkill, fieldGroups: interlocutoryApplicationFieldGroups },
  { value: 'vakalatnama', label: 'Vakalatnama', skillName: 'indian-vakalatnama-generator', skillContent: vakalatnamaSkill, fieldGroups: vakalatnamaFieldGroups },
  { value: 'review-petition', label: 'Review Petition / Application', skillName: 'indian-review-petition-generator', skillContent: reviewPetitionSkill, fieldGroups: reviewPetitionFieldGroups },
  { value: 'writ-certiorari', label: 'Writ Petition - Certiorari', skillName: 'indian-writ-certiorari-generator', skillContent: writCertiorariSkill, fieldGroups: writFieldGroups },
  { value: 'writ-habeas-corpus', label: 'Writ Petition - Habeas Corpus', skillName: 'indian-writ-habeas-corpus-generator', skillContent: writHabeasCorpusSkill, fieldGroups: writFieldGroups },
  { value: 'writ-mandamus', label: 'Writ Petition - Mandamus', skillName: 'indian-writ-mandamus-generator', skillContent: writMandamusSkill, fieldGroups: writFieldGroups },
  { value: 'writ-prohibition', label: 'Writ Petition - Prohibition', skillName: 'indian-writ-prohibition-generator', skillContent: writProhibitionSkill, fieldGroups: writFieldGroups },
  { value: 'writ-quo-warranto', label: 'Writ Petition - Quo Warranto', skillName: 'indian-writ-quo-warranto-generator', skillContent: writQuoWarrantoSkill, fieldGroups: writFieldGroups },
  { value: 'convertible-note', label: 'Convertible Note', skillName: 'indian-convertible-note-generator', skillContent: convertibleNoteSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'safe-note', label: 'SAFE / Future Equity Agreement', skillName: 'indian-safe-generator', skillContent: safeNoteSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'incorporation-certificate', label: 'Company Incorporation / Corporate Certificate', skillName: 'indian-company-certificate-generator', skillContent: incorporationCertificateSkill, fieldGroups: companyCertificateFieldGroups },
  { value: 'mca-roc-filing', label: 'MCA / ROC Filing Draft', skillName: 'indian-mca-roc-filing-generator', skillContent: mcaRocFilingSkill, fieldGroups: mcaRocFieldGroups },
  { value: 'share-transfer-agreement', label: 'Share Transfer Agreement', skillName: 'indian-share-transfer-agreement-generator', skillContent: shareTransferAgreementSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'ma-agreement', label: 'M&A / Acquisition Agreement', skillName: 'indian-ma-agreement-generator', skillContent: maAgreementSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'moa', label: 'Memorandum of Association', skillName: 'indian-moa-generator', skillContent: moaSkill, fieldGroups: moaFieldGroups },
  { value: 'software-license-agreement', label: 'Software License Agreement', skillName: 'indian-software-license-agreement-generator', skillContent: softwareLicenseAgreementSkill, fieldGroups: softwareLicenseFieldGroups },
  { value: 'saas-agreement', label: 'SaaS Agreement', skillName: 'indian-saas-agreement-generator', skillContent: saasAgreementSkill, fieldGroups: saasFieldGroups },
  { value: 'software-development-agreement', label: 'Software Development Agreement', skillName: 'indian-software-development-agreement-generator', skillContent: softwareDevelopmentAgreementSkill, fieldGroups: servicesAgreementFieldGroups },
  { value: 'franchise-agreement', label: 'Franchise Agreement', skillName: 'indian-franchise-agreement-generator', skillContent: franchiseAgreementSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'rent-agreement', label: 'Rent Agreement', skillName: 'indian-rent-agreement-generator', skillContent: rentAgreementSkill, fieldGroups: propertyAgreementFieldGroups },
  { value: 'lease-deed', label: 'Lease Deed', skillName: 'indian-lease-deed-generator', skillContent: leaseDeedSkill, fieldGroups: propertyAgreementFieldGroups },
  { value: 'shareholders-agreement', label: 'Shareholders Agreement', skillName: 'indian-shareholders-agreement-generator', skillContent: shareholdersAgreementSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'joint-venture-agreement', label: 'Joint Venture Agreement', skillName: 'indian-joint-venture-agreement-generator', skillContent: jointVentureAgreementSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'partnership-deed', label: 'Partnership Deed', skillName: 'indian-partnership-deed-generator', skillContent: partnershipDeedSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'consultancy-agreement', label: 'Consultancy Agreement', skillName: 'indian-consultancy-agreement-generator', skillContent: consultancyAgreementSkill, fieldGroups: servicesAgreementFieldGroups },
  { value: 'vendor-agreement', label: 'Vendor Agreement', skillName: 'indian-vendor-agreement-generator', skillContent: vendorAgreementSkill, fieldGroups: servicesAgreementFieldGroups },
  { value: 'freelance-agreement', label: 'Freelance Agreement', skillName: 'indian-freelance-agreement-generator', skillContent: freelanceAgreementSkill, fieldGroups: servicesAgreementFieldGroups },
  { value: 'employment-agreement', label: 'Employment Agreement', skillName: 'indian-employment-agreement-generator', skillContent: employmentAgreementSkill, fieldGroups: employmentAgreementFieldGroups },
  { value: 'employment-agreement-esop', label: 'Employment Agreement with ESOP', skillName: 'indian-employment-esop-agreement-generator', skillContent: employmentAgreementEsopSkill, fieldGroups: employmentEsopFieldGroups },
  { value: 'independent-contractor-agreement', label: 'Independent Contractor Agreement', skillName: 'indian-independent-contractor-agreement-generator', skillContent: independentContractorAgreementSkill, fieldGroups: servicesAgreementFieldGroups },
  { value: 'mou', label: 'Memorandum of Understanding', skillName: 'indian-mou-generator', skillContent: mouSkill, fieldGroups: corporateTransactionFieldGroups },
  { value: 'contempt-petition', label: 'Contempt Petition', skillName: 'indian-contempt-petition-generator', skillContent: contemptPetitionSkill, fieldGroups: contemptPetitionFieldGroups },
  { value: 'evidence-affidavit', label: 'Evidence by Way of Affidavit', skillName: 'indian-evidence-affidavit-generator', skillContent: evidenceAffidavitSkill, fieldGroups: evidenceAffidavitFieldGroups },
  { value: 'notice-reply', label: 'Reply to Legal Notice', skillName: 'indian-notice-reply-generator', skillContent: noticeReplySkill, fieldGroups: noticeReplyFieldGroups },
  { value: 'anticipatory-bail-application', label: 'Anticipatory Bail Application', skillName: 'indian-anticipatory-bail-generator', skillContent: anticipatoryBailApplicationSkill, fieldGroups: anticipatoryBailFieldGroups },
];

export function getDocumentSkillByType(documentType: string): DocumentSkillDefinition | null {
  return DOCUMENT_SKILLS.find((skill) => skill.value === documentType) ?? null;
}
