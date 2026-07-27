import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { renderToStaticMarkup } from 'react-dom/server';
import { BookOpen, ChevronDown, Download, FileText, Loader2, LogOut, PanelLeft, Plus, Shield, Wand2, X } from 'lucide-react';
import { DOCUMENT_SKILLS, getDocumentSkillByType } from './documentSkills';
import { type DocumentFieldGroup, type DocumentFieldSchema } from './documentFieldSchemas';

export interface StructuredDocumentSectionItem {
  key: string;
  label: string;
  value: string;
}

export interface StructuredDocumentSection {
  key: string;
  title: string;
  items: StructuredDocumentSectionItem[];
}

export interface DocumentDraft {
  documentType: string;
  additionalInfo: string;
  structuredFields: Record<string, string>;
  structuredSections: StructuredDocumentSection[];
  document: string;
}

export interface DocumentGeneratorInput {
  documentType: string;
  additionalInfo: string;
  structuredFields: Record<string, string>;
  structuredSections: StructuredDocumentSection[];
  partyDetails: string;
  recipientDetails: string;
  caseDetails: string;
  relevantInfo: string;
}

interface DocumentGeneratorProps {
  draft: DocumentDraft | null;
  isGenerating?: boolean;
  error?: string | null;
  userName: string;
  onLogout: () => void;
  onCreateNew: () => void;
  history?: Array<{
    artifact_id: string;
    title: string;
    created_at: string;
    updated_at: string;
  }>;
  activeHistoryId?: string | null;
  onSelectHistory?: (artifactId: string) => void;
  onGenerate: (input: DocumentGeneratorInput) => Promise<void>;
}

const emptyInput = {
  documentType: '',
  additionalInfo: '',
  structuredFields: {} as Record<string, string>,
};

interface ContractTermInfo {
  value: string;
  error: string | null;
}

function parseDateInput(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsedDate = new Date(Date.UTC(year, month - 1, day));

  if (
    Number.isNaN(parsedDate.getTime()) ||
    parsedDate.getUTCFullYear() !== year ||
    parsedDate.getUTCMonth() !== month - 1 ||
    parsedDate.getUTCDate() !== day
  ) {
    return null;
  }

  return { year, month, day, date: parsedDate };
}

function getDaysInMonth(year: number, month: number) {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

function calculateContractTerm(startDateValue: string, endDateValue: string): ContractTermInfo {
  if (!startDateValue || !endDateValue) {
    return { value: '', error: null };
  }

  const start = parseDateInput(startDateValue);
  const end = parseDateInput(endDateValue);

  if (!start || !end) {
    return { value: '', error: 'Enter valid contract start and end dates.' };
  }

  if (end.date.getTime() < start.date.getTime()) {
    return { value: '', error: 'End date must be on or after start date.' };
  }

  let years = end.year - start.year;
  let months = end.month - start.month;
  let days = end.day - start.day;

  if (days < 0) {
    months -= 1;
    const previousMonth = end.month === 1 ? 12 : end.month - 1;
    const previousMonthYear = previousMonth === 12 ? end.year - 1 : end.year;
    days += getDaysInMonth(previousMonthYear, previousMonth);
  }

  if (months < 0) {
    years -= 1;
    months += 12;
  }

  const parts = [
    years > 0 ? `${years} year${years === 1 ? '' : 's'}` : '',
    months > 0 ? `${months} month${months === 1 ? '' : 's'}` : '',
    days > 0 ? `${days} day${days === 1 ? '' : 's'}` : '',
  ].filter(Boolean);

  return {
    value: parts.length > 0 ? parts.join(', ') : '0 days',
    error: null,
  };
}

function preserveDocumentLineBreaks(document: string) {
  return document
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line) => {
      if (!line.trim()) {
        return '';
      }

      const trimmed = line.trim();
      if (
        trimmed === '---' ||
        trimmed === '___' ||
        trimmed === '***' ||
        /^#{1,6}\s/.test(trimmed) ||
        /^(\d+\.|[-*+])\s/.test(trimmed) ||
        trimmed.startsWith('|') ||
        trimmed.startsWith('+')
      ) {
        return line;
      }

      return `${line}  `;
    })
    .join('\n');
}

function downloadBlob(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

function downloadDocumentTxt(document: string) {
  downloadBlob('document-draft.txt', document, 'text/plain;charset=utf-8');
}

function downloadDocumentDoc(documentText: string) {
  const escapeHtml = (str: string) =>
    str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

  const rawLines = documentText
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n');

  const blocks: string[][] = [];
  let current: string[] = [];

  for (const raw of rawLines) {
    if (raw.trim() === '') {
      if (current.length > 0) {
        blocks.push(current);
        current = [];
      }
      blocks.push([]);
    } else {
      current.push(raw);
    }
  }
  if (current.length > 0) blocks.push(current);

  const paragraphs = blocks
    .map((block) => {
      if (block.length === 0) {
        return '<p>&nbsp;</p>';
      }
      const html = block
        .map((line) => escapeHtml(line).replace(/\*\*(.*?)\*\*/g, '<b>$1</b>'))
        .join('<br>');
      return `<p>${html}</p>`;
    })
    .join('\n');

  const htmlDocument = `<!doctype html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40">
  <head>
    <meta charset="utf-8" />
    <title>Document Draft</title>
    <!--[if gte mso 9]><xml>
      <w:WordDocument>
        <w:View>Print</w:View>
        <w:Zoom>100</w:Zoom>
        <w:DoNotOptimizeForBrowser/>
      </w:WordDocument>
    </xml><![endif]-->
    <style>
      @page { size: A4; margin: 2.54cm 2.54cm 2.54cm 2.54cm; }
      body {
        font-family: 'Calibri', 'Arial', 'Helvetica', sans-serif;
        font-size: 11pt;
        line-height: 1.5;
        color: #000000;
      }
      p { margin: 0 0 6pt 0; text-align: justify; }
    </style>
  </head>
  <body>
    ${paragraphs}
  </body>
</html>`;
  downloadBlob('document-draft.doc', htmlDocument, 'application/msword');
}

function buildStructuredSections(
  fieldGroups: DocumentFieldGroup[],
  structuredFields: Record<string, string>,
  additionalInfo: string,
): StructuredDocumentSection[] {
  const sections = fieldGroups
    .map((group) => ({
      key: group.key,
      title: group.title,
      items: (() => {
        const items = group.fields
          .map((field) => ({
          key: field.key,
          label: field.label,
          value: (structuredFields[field.key] || '').trim(),
        }))
          .filter((item) => item.value);

        const contractTerm = calculateContractTerm(
          structuredFields.start_date || '',
          structuredFields.end_date || '',
        );

        if (
          !contractTerm.error &&
          contractTerm.value &&
          group.fields.some((field) => field.key === 'start_date') &&
          group.fields.some((field) => field.key === 'end_date')
        ) {
          items.push({
            key: 'term',
            label: 'Term',
            value: contractTerm.value,
          });
        }

        return items;
      })(),
    }))
    .filter((group) => group.items.length > 0);

  if (additionalInfo.trim()) {
    sections.push({
      key: 'additional-info',
      title: 'Additional Information',
      items: [{ key: 'additional_info', label: 'Additional Information', value: additionalInfo.trim() }],
    });
  }

  return sections;
}

function stringifySection(section: StructuredDocumentSection) {
  return section.items.map((item) => `${item.label}: ${item.value}`).join('\n');
}

function buildLegacyPayload(sectionMap: Map<string, StructuredDocumentSection>, additionalInfo: string) {
  const partyDetails = stringifySection(sectionMap.get('party-details') || { key: '', title: '', items: [] });
  const recipientDetails = stringifySection(sectionMap.get('recipient-details') || { key: '', title: '', items: [] });

  const caseSections = ['court-proceeding-details', 'matter-details', 'financial-terms', 'property-details']
    .map((key) => sectionMap.get(key))
    .filter((section): section is StructuredDocumentSection => Boolean(section))
    .map((section) => `${section.title}\n${stringifySection(section)}`)
    .join('\n\n');

  const relevantSections = ['signatures-witnesses']
    .map((key) => sectionMap.get(key))
    .filter((section): section is StructuredDocumentSection => Boolean(section))
    .map((section) => `${section.title}\n${stringifySection(section)}`)
    .join('\n\n');

  return {
    partyDetails,
    recipientDetails,
    caseDetails: caseSections,
    relevantInfo: [relevantSections, additionalInfo.trim()].filter(Boolean).join('\n\n'),
  };
}

function renderField(
  field: DocumentFieldSchema,
  value: string,
  onChange: (fieldKey: string, value: string) => void,
) {
  const commonProps = {
    id: field.key,
    className: 'text-field',
    value,
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      onChange(field.key, event.target.value),
    required: field.required,
  };

  if (field.type === 'textarea') {
    return (
      <textarea
        {...commonProps}
        className="text-field resize-y"
        rows={field.rows || 4}
        placeholder={field.placeholder}
      />
    );
  }

  if (field.type === 'select') {
    return (
      <select {...commonProps}>
        <option value="">Select</option>
        {(field.options || []).map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  return (
    <input
      {...commonProps}
      type={field.type}
      placeholder={field.placeholder}
    />
  );
}

export const DocumentGenerator: React.FC<DocumentGeneratorProps> = ({
  draft,
  isGenerating = false,
  error,
  userName,
  onLogout,
  onCreateNew,
  history = [],
  activeHistoryId = null,
  onSelectHistory,
  onGenerate,
}) => {
  const [form, setForm] = useState(emptyInput);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    return window.innerWidth >= 768;
  });

  const selectedSkill = useMemo(() => getDocumentSkillByType(form.documentType), [form.documentType]);
  const contractTerm = useMemo(
    () => calculateContractTerm(form.structuredFields.start_date || '', form.structuredFields.end_date || ''),
    [form.structuredFields.end_date, form.structuredFields.start_date],
  );
  const previewDocument = useMemo(
    () => (draft?.document ? preserveDocumentLineBreaks(draft.document) : ''),
    [draft?.document],
  );

  useEffect(() => {
    setForm((current) => ({
      ...current,
      structuredFields: selectedSkill
        ? Object.fromEntries(
            selectedSkill.fieldGroups.flatMap((group) =>
              group.fields.map((field) => [field.key, current.structuredFields[field.key] || '']),
            ),
          )
        : {},
    }));
  }, [selectedSkill?.value]);

  useEffect(() => {
    if (!draft) {
      setForm(emptyInput);
      return;
    }
    setForm({
      documentType: draft.documentType,
      additionalInfo: draft.additionalInfo,
      structuredFields: draft.structuredFields,
    });
  }, [draft]);

  const missingRequiredFields = useMemo(() => {
    if (!selectedSkill) {
      return [];
    }

    return selectedSkill.fieldGroups.flatMap((group) =>
      group.fields.filter((field) => field.required && !(form.structuredFields[field.key] || '').trim()),
    );
  }, [form.structuredFields, selectedSkill]);

  const canGenerate =
    Boolean(selectedSkill) &&
    missingRequiredFields.length === 0 &&
    !contractTerm.error &&
    !isGenerating;

  const updateField = (field: 'documentType' | 'additionalInfo', value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const updateStructuredField = (fieldKey: string, value: string) => {
    setForm((current) => ({
      ...current,
      structuredFields: { ...current.structuredFields, [fieldKey]: value },
    }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedSkill || !canGenerate) {
      return;
    }

    const normalizedStructuredFields = {
      ...form.structuredFields,
      ...(contractTerm.value ? { term: contractTerm.value } : {}),
    };

    const structuredSections = buildStructuredSections(
      selectedSkill.fieldGroups,
      normalizedStructuredFields,
      form.additionalInfo,
    );
    const sectionMap = new Map(structuredSections.map((section) => [section.key, section]));
    const legacyPayload = buildLegacyPayload(sectionMap, form.additionalInfo);

    await onGenerate({
      documentType: form.documentType,
      additionalInfo: form.additionalInfo,
      structuredFields: normalizedStructuredFields,
      structuredSections,
      ...legacyPayload,
    });
  };

  return (
    <div className="relative flex h-full min-h-0 overflow-hidden bg-surface">
      {isSidebarOpen ? (
        <>
          <button
            type="button"
            aria-label="Close sidebar overlay"
            onClick={() => setIsSidebarOpen(false)}
            className="absolute inset-0 z-30 bg-black/40 md:hidden"
          />

          <aside className="absolute inset-y-0 left-0 z-40 flex h-full w-72 shrink-0 flex-col overflow-hidden border-r border-outline-variant/20 bg-surface-container shadow-ambient md:relative md:z-0 md:shadow-none">
        <div className="shrink-0 border-b border-outline-variant/20 bg-surface-container p-4">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-on-primary">
                <BookOpen size={18} />
              </div>
              <div>
                <div className="text-sm font-semibold text-on-surface">LAW LLM Workspace</div>
                <div className="text-xs text-on-surface-variant">{userName}</div>
              </div>
            </div>
            <button
              type="button"
              aria-label="Close sidebar"
              onClick={() => setIsSidebarOpen(false)}
              className="flex h-9 w-9 items-center justify-center rounded-2xl border border-outline-variant/40 bg-surface-container-low text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
            >
              <X size={16} />
            </button>
          </div>

          <button type="button" onClick={onCreateNew} className="primary-button w-full justify-center">
            <Plus size={16} />
            New Document
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <div className="mb-3 flex items-center gap-2 px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
            <Shield size={13} />
            Document History
          </div>
          <div className="space-y-2">
            {history.map((item) => (
              <button
                key={item.artifact_id}
                type="button"
                onClick={() => onSelectHistory?.(item.artifact_id)}
                className={[
                  'w-full rounded-2xl border px-3 py-3 text-left transition',
                  item.artifact_id === activeHistoryId
                    ? 'border-primary/35 bg-primary/10 text-on-surface'
                    : 'border-outline-variant/30 bg-surface-container-low hover:border-primary/20 hover:bg-surface-container-high',
                ].join(' ')}
              >
                <div className="truncate text-sm font-medium">{item.title}</div>
                <div className="text-xs text-on-surface-variant">
                  Updated {new Date(item.updated_at).toLocaleDateString()}
                </div>
              </button>
            ))}
            {history.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-low px-4 py-5 text-sm text-on-surface-variant">
                No saved documents yet.
              </div>
            ) : null}
          </div>
        </div>

        <div className="shrink-0 border-t border-outline-variant/20 bg-surface-container p-3">
          <button type="button" onClick={onLogout} className="neutral-button w-full justify-center">
            <LogOut size={16} />
            Logout
          </button>
        </div>
          </aside>
        </>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="sticky top-0 z-30 shrink-0 border-b border-outline-variant/20 bg-surface-container px-4 py-4 md:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
              onClick={() => setIsSidebarOpen((current) => !current)}
              className="flex h-10 w-10 items-center justify-center rounded-2xl border border-outline-variant/40 bg-surface-container-low text-on-surface-variant transition hover:border-primary/30 hover:text-on-surface"
            >
              <PanelLeft size={18} />
            </button>
            <div>
              <div className="section-kicker">DOCUMENT DRAFTING</div>
              <h1 className="mt-1 text-xl font-semibold text-on-surface">Document Generator</h1>
            </div>
          </div>
          {draft?.document ? (
            <div className="relative">
              <button type="button" onClick={() => setIsExportMenuOpen((current) => !current)} className="primary-button">
                <Download size={18} />
                Export
                <ChevronDown size={16} />
              </button>
              {isExportMenuOpen ? (
                <div className="absolute right-0 top-full z-20 mt-2 min-w-40 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-2 shadow-ambient">
                  <button
                    type="button"
                    onClick={() => {
                      downloadDocumentTxt(draft.document);
                      setIsExportMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-on-surface transition hover:bg-surface-container-low"
                  >
                    <FileText size={16} />
                    Export TXT
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      downloadDocumentDoc(draft.document);
                      setIsExportMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-on-surface transition hover:bg-surface-container-low"
                  >
                    <FileText size={16} />
                    Export DOC
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-[420px_1fr]">
          <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-outline-variant/40 bg-surface-container-low p-4">
            <div>
              <label className="field-label" htmlFor="documentType">
                Type of document <span className="field-required">*</span>
              </label>
              <select
                id="documentType"
                className="text-field"
                value={form.documentType}
                onChange={(event) => updateField('documentType', event.target.value)}
                required
              >
                <option value="">Select</option>
                {DOCUMENT_SKILLS.map((documentOption) => (
                  <option key={documentOption.value} value={documentOption.value}>
                    {documentOption.label}
                  </option>
                ))}
              </select>
            </div>

            {selectedSkill ? (
              <>
                {selectedSkill.fieldGroups.map((group) => (
                  <div key={group.key} className="space-y-3 rounded-xl border border-outline-variant/20 bg-surface-container-lowest/40 p-3">
                    <div className="text-sm font-semibold text-on-surface">{group.title}</div>
                    {group.fields.map((field) => (
                      <div key={field.key}>
                        <label className="field-label" htmlFor={field.key}>
                          {field.label}
                          {field.required ? <span className="field-required"> *</span> : null}
                        </label>
                        {renderField(field, form.structuredFields[field.key] || '', updateStructuredField)}
                      </div>
                    ))}
                    {group.fields.some((field) => field.key === 'start_date') &&
                    group.fields.some((field) => field.key === 'end_date') ? (
                      contractTerm.error ? (
                        <div className="rounded-lg border border-error/30 bg-error-container/40 px-3 py-2 text-sm text-on-error-container">
                          {contractTerm.error}
                        </div>
                      ) : contractTerm.value ? (
                        <div className="rounded-lg border border-outline-variant/30 bg-surface-container-low px-3 py-2 text-sm text-on-surface-variant">
                          Calculated term: <span className="text-on-surface">{contractTerm.value}</span>
                        </div>
                      ) : null
                    ) : null}
                  </div>
                ))}

                <div>
                  <label className="field-label" htmlFor="additionalInfo">
                    Additional Information
                  </label>
                  <textarea
                    id="additionalInfo"
                    className="text-field min-h-24 resize-y"
                    value={form.additionalInfo}
                    onChange={(event) => updateField('additionalInfo', event.target.value)}
                    placeholder="Optional notes, formatting instructions, annexures, policy references, or extra facts"
                  />
                </div>
              </>
            ) : null}

            <button type="submit" className="primary-button w-full" disabled={!canGenerate}>
              {isGenerating ? <Loader2 className="animate-spin" size={18} /> : <Wand2 size={18} />}
              Generate Document
            </button>

            {!canGenerate && selectedSkill && missingRequiredFields.length > 0 ? (
              <div className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest p-3 text-sm text-on-surface-variant">
                Fill required fields: {missingRequiredFields.map((field) => field.label).join(', ')}
              </div>
            ) : null}

            {error ? (
              <div className="rounded-lg border border-error/30 bg-error-container/40 p-3 text-sm text-on-error-container">
                {error}
              </div>
            ) : null}
          </form>

          <div className="min-h-[520px] rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-5">
            {isGenerating ? (
              <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 text-on-surface-variant">
                <Loader2 className="animate-spin text-primary" size={30} />
                <div className="text-sm">Preparing document draft...</div>
              </div>
            ) : draft?.document ? (
              <div className="prose prose-sm max-w-none whitespace-pre-wrap dark:prose-invert prose-headings:text-on-surface prose-p:my-0 prose-p:leading-relaxed prose-li:my-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{previewDocument}</ReactMarkdown>
              </div>
            ) : (
              <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center text-on-surface-variant">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText size={28} />
                </div>
                <h2 className="text-lg font-semibold text-on-surface">Your generated document will appear here</h2>
                <p className="mt-2 max-w-md text-sm">
                  Choose a document type first. The form will switch to the exact fields that document needs.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default DocumentGenerator;
