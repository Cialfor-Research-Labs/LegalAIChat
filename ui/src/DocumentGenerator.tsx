import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { renderToStaticMarkup } from 'react-dom/server';
import { ChevronDown, Download, FileText, Loader2, Wand2 } from 'lucide-react';
import { DOCUMENT_SKILLS } from './documentSkills';

export interface DocumentDraft {
  documentType: string;
  partyDetails: string;
  recipientDetails: string;
  caseDetails: string;
  relevantInfo: string;
  document: string;
}

interface DocumentGeneratorProps {
  draft: DocumentDraft | null;
  isGenerating?: boolean;
  error?: string | null;
  onGenerate: (input: Omit<DocumentDraft, 'document'>) => Promise<void>;
}

const emptyInput = {
  documentType: '',
  partyDetails: '',
  recipientDetails: '',
  caseDetails: '',
  relevantInfo: '',
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

export const DocumentGenerator: React.FC<DocumentGeneratorProps> = ({
  draft,
  isGenerating = false,
  error,
  onGenerate,
}) => {
  const [form, setForm] = useState(emptyInput);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);

  const canGenerate = useMemo(
    () => form.documentType.trim().length > 0 && form.caseDetails.trim().length >= 5 && !isGenerating,
    [form.caseDetails, form.documentType, isGenerating],
  );
  const previewDocument = useMemo(
    () => (draft?.document ? preserveDocumentLineBreaks(draft.document) : ''),
    [draft?.document],
  );

  const updateField = (field: keyof typeof emptyInput, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canGenerate) return;
    await onGenerate(form);
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
              <button
                type="button"
                onClick={() => setIsExportMenuOpen((current) => !current)}
                className="primary-button"
              >
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
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-lg border border-outline-variant/40 bg-surface-container-low p-4"
          >
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

            <div>
              <label className="field-label" htmlFor="partyDetails">
                Party / client details
              </label>
              <textarea
                id="partyDetails"
                className="text-field min-h-24 resize-y"
                value={form.partyDetails}
                onChange={(event) => updateField('partyDetails', event.target.value)}
                placeholder="Names, addresses, business details, and relationship to the matter"
              />
            </div>

            <div>
              <label className="field-label" htmlFor="recipientDetails">
                Other party / recipient details
              </label>
              <textarea
                id="recipientDetails"
                className="text-field min-h-24 resize-y"
                value={form.recipientDetails}
                onChange={(event) => updateField('recipientDetails', event.target.value)}
                placeholder="Recipient, company, address, designation, or any involved party"
              />
            </div>

            <div>
              <label className="field-label" htmlFor="caseDetails">
                Core details <span className="field-required">*</span>
              </label>
              <textarea
                id="caseDetails"
                className="text-field min-h-36 resize-y"
                value={form.caseDetails}
                onChange={(event) => updateField('caseDetails', event.target.value)}
                placeholder="Facts, purpose, dates, requested clauses, and what the document should achieve"
                required
              />
            </div>

            <div>
              <label className="field-label" htmlFor="relevantInfo">
                Any other relevant information
              </label>
              <textarea
                id="relevantInfo"
                className="text-field min-h-24 resize-y"
                value={form.relevantInfo}
                onChange={(event) => updateField('relevantInfo', event.target.value)}
                placeholder="Formatting instructions, annexures, names, document references, or extra notes"
              />
            </div>

            <button type="submit" className="primary-button w-full" disabled={!canGenerate}>
              {isGenerating ? <Loader2 className="animate-spin" size={18} /> : <Wand2 size={18} />}
              Generate Document
            </button>

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
                  Choose a document type, add the relevant parties and facts, and this tab will be ready for backend integration later.
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
