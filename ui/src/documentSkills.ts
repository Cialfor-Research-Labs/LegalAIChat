import affidavitSkill from '../../document-generator-skills/affidavit/SKILL.md?raw';
import interlocutoryApplicationSkill from '../../document-generator-skills/interlocutory-application/SKILL.md?raw';
import plaintSkill from '../../document-generator-skills/plaint/SKILL.md?raw';
import reviewPetitionSkill from '../../document-generator-skills/review-petition/SKILL.md?raw';
import vakalatnamaSkill from '../../document-generator-skills/vakalatnama/SKILL.md?raw';
import writCertiorariSkill from '../../document-generator-skills/writ-certiorari/SKILL.md?raw';
import writHabeasCorpusSkill from '../../document-generator-skills/writ-habeas-corpus/SKILL.md?raw';
import writMandamusSkill from '../../document-generator-skills/writ-mandamus/SKILL.md?raw';
import writProhibitionSkill from '../../document-generator-skills/writ-prohibition/SKILL.md?raw';
import writQuoWarrantoSkill from '../../document-generator-skills/writ-quo-warranto/SKILL.md?raw';
import writtenStatementSkill from '../../document-generator-skills/written-statement/SKILL.md?raw';

export interface DocumentSkillDefinition {
  value: string;
  label: string;
  skillName: string;
  skillContent: string;
}

export const DOCUMENT_SKILLS: DocumentSkillDefinition[] = [
  { value: 'plaint', label: 'Civil Plaint', skillName: 'indian-plaint-generator', skillContent: plaintSkill },
  {
    value: 'written-statement',
    label: 'Written Statement',
    skillName: 'indian-written-statement-generator',
    skillContent: writtenStatementSkill,
  },
  { value: 'affidavit', label: 'Affidavit', skillName: 'indian-affidavit-generator', skillContent: affidavitSkill },
  {
    value: 'interlocutory-application',
    label: 'Interlocutory Application',
    skillName: 'indian-interlocutory-application-generator',
    skillContent: interlocutoryApplicationSkill,
  },
  {
    value: 'vakalatnama',
    label: 'Vakalatnama',
    skillName: 'indian-vakalatnama-generator',
    skillContent: vakalatnamaSkill,
  },
  {
    value: 'review-petition',
    label: 'Review Petition / Application',
    skillName: 'indian-review-petition-generator',
    skillContent: reviewPetitionSkill,
  },
  {
    value: 'writ-certiorari',
    label: 'Writ Petition - Certiorari',
    skillName: 'indian-writ-certiorari-generator',
    skillContent: writCertiorariSkill,
  },
  {
    value: 'writ-habeas-corpus',
    label: 'Writ Petition - Habeas Corpus',
    skillName: 'indian-writ-habeas-corpus-generator',
    skillContent: writHabeasCorpusSkill,
  },
  {
    value: 'writ-mandamus',
    label: 'Writ Petition - Mandamus',
    skillName: 'indian-writ-mandamus-generator',
    skillContent: writMandamusSkill,
  },
  {
    value: 'writ-prohibition',
    label: 'Writ Petition - Prohibition',
    skillName: 'indian-writ-prohibition-generator',
    skillContent: writProhibitionSkill,
  },
  {
    value: 'writ-quo-warranto',
    label: 'Writ Petition - Quo Warranto',
    skillName: 'indian-writ-quo-warranto-generator',
    skillContent: writQuoWarrantoSkill,
  },
];

export function getDocumentSkillByType(documentType: string): DocumentSkillDefinition | null {
  return DOCUMENT_SKILLS.find((skill) => skill.value === documentType) ?? null;
}
