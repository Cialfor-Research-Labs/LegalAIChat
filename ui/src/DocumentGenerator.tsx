import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { renderToStaticMarkup } from 'react-dom/server';
import { ChevronDown, Download, FileText, Loader2, Wand2 } from 'lucide-react';
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
  onGenerate: (input: DocumentGeneratorInput) => Promise<void>;
}

const emptyInput = {
  documentType: '',
  additionalInfo: '',
  structuredFields: {} as Record<string, string>,
};

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
        /^(\d+\.|[-*+])\s/.test(trimmed)
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

function downloadDocumentDoc(document: string) {
  const previewHtml = renderToStaticMarkup(
    <ReactMarkdown>{preserveDocumentLineBreaks(document)}</ReactMarkdown>,
  );
  const htmlDocument = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Document Draft</title>
  </head>
  <body style="font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.5; color: #111827; margin: 36pt;">
    <div style="white-space: pre-wrap;">
      ${previewHtml}
    </div>
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
      items: group.fields
        .map((field) => ({
          key: field.key,
          label: field.label,
          value: (structuredFields[field.key] || '').trim(),
        }))
        .filter((item) => item.value),
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
  onGenerate,
}) => {
  const [form, setForm] = useState(emptyInput);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);

  const selectedSkill = useMemo(() => getDocumentSkillByType(form.documentType), [form.documentType]);
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

  const missingRequiredFields = useMemo(() => {
    if (!selectedSkill) {
      return [];
    }

    return selectedSkill.fieldGroups.flatMap((group) =>
      group.fields.filter((field) => field.required && !(form.structuredFields[field.key] || '').trim()),
    );
  }, [form.structuredFields, selectedSkill]);

  const canGenerate = Boolean(selectedSkill) && missingRequiredFields.length === 0 && !isGenerating;

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

    const structuredSections = buildStructuredSections(
      selectedSkill.fieldGroups,
      form.structuredFields,
      form.additionalInfo,
    );
    const sectionMap = new Map(structuredSections.map((section) => [section.key, section]));
    const legacyPayload = buildLegacyPayload(sectionMap, form.additionalInfo);

    await onGenerate({
      documentType: form.documentType,
      additionalInfo: form.additionalInfo,
      structuredFields: form.structuredFields,
      structuredSections,
      ...legacyPayload,
    });
  };

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="border-b border-outline-variant/20 bg-surface-container px-4 py-4 md:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <div>
            <div className="section-kicker">DOCUMENT DRAFTING</div>
            <h1 className="mt-1 text-xl font-semibold text-on-surface">Document Generator</h1>
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
                <ReactMarkdown>{previewDocument}</ReactMarkdown>
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
  );
};

export default DocumentGenerator;
