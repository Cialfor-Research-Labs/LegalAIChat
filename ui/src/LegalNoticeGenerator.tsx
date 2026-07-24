import React, { useEffect, useMemo, useState } from 'react';
import { BookOpen, ChevronDown, Download, FileText, Loader2, LogOut, PanelLeft, Plus, Shield, Wand2, X } from 'lucide-react';

export interface LegalNoticeDraft {
  clientDetails: string;
  lawyerDetails: string;
  recipientDetails: string;
  caseDetails: string;
  relevantInfo: string;
  notice: string;
}

interface LegalNoticeGeneratorProps {
  draft: LegalNoticeDraft | null;
  initialCaseDetails?: string;
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
  onGenerate: (input: Omit<LegalNoticeDraft, 'notice'>) => Promise<void>;
}

const emptyInput = {
  clientDetails: '',
  lawyerDetails: '',
  recipientDetails: '',
  caseDetails: '',
  relevantInfo: '',
};

function downloadBlob(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

function downloadNoticeTxt(notice: string) {
  downloadBlob('legal-notice.txt', notice, 'text/plain;charset=utf-8');
}

/**
 * Normalize a notice line that the LLM may have emitted with space-padded
 * multi-column alignment (e.g. "Adv.          Neha          Singh").
 *
 * In the web app such lines are rendered with white-space:pre-wrap inside a
 * narrow panel so they soft-wrap and look fine. In a Word document on a full
 * A4 page the spaces spread the words far apart. We detect lines that contain
 * two or more consecutive spaces and collapse each run of multiple spaces
 * down to a single space so the text reads naturally in a proportional font.
 *
 * Lines that are genuinely wide (e.g. the body paragraphs) rarely contain
 * runs of multiple spaces, so collapsing only affects the padded header lines.
 */
function normalizeNoticeLine(line: string): string {
  // If the line has 2+ consecutive spaces it was space-padded for columns.
  // Collapse every run of 2+ spaces to a single space.
  if (/  /.test(line)) {
    return line.replace(/ {2,}/g, ' ').trim();
  }
  return line;
}

/**
 * Convert plain-text legal notice to a Word-compatible HTML document.
 *
 * Uses Times New Roman with proper paragraph spacing. Lines that contain
 * space-padded multi-column alignment (LLM letterhead artefacts) are
 * normalised to single-column text so they render correctly on a full-width
 * A4 page in a proportional font.
 */
function downloadNoticeDoc(notice: string) {
  const escapeHtml = (str: string) =>
    str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

  const rawLines = notice
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n');

  // Group consecutive non-blank lines into paragraph blocks separated by
  // blank lines. Each block becomes one <p> with <br> between its lines.
  const blocks: string[][] = [];
  let current: string[] = [];

  for (const raw of rawLines) {
    const normalized = normalizeNoticeLine(raw);
    if (normalized === '') {
      if (current.length > 0) {
        blocks.push(current);
        current = [];
      }
      // Push an empty block to preserve blank-line spacing
      blocks.push([]);
    } else {
      current.push(normalized);
    }
  }
  if (current.length > 0) blocks.push(current);

  const paragraphs = blocks
    .map((block) => {
      if (block.length === 0) {
        // Blank paragraph for spacing
        return '<p>&nbsp;</p>';
      }
      const html = block.map((line) => escapeHtml(line)).join('<br>');
      return `<p>${html}</p>`;
    })
    .join('\n');

  const htmlDocument = `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40">
<head>
  <meta charset="utf-8"/>
  <title>Legal Notice</title>
  <!--[if gte mso 9]>
  <xml>
    <w:WordDocument>
      <w:View>Print</w:View>
      <w:Zoom>100</w:Zoom>
      <w:DoNotOptimizeForBrowser/>
    </w:WordDocument>
  </xml>
  <![endif]-->
  <style>
    @page {
      size: A4;
      margin: 2.54cm 2.54cm 2.54cm 2.54cm;
    }
    body {
      font-family: "Times New Roman", Times, serif;
      font-size: 12pt;
      line-height: 1.6;
      color: #000000;
    }
    p {
      margin: 0 0 6pt 0;
      padding: 0;
    }
  </style>
</head>
<body>
${paragraphs}
</body>
</html>`;

  downloadBlob('legal-notice.doc', htmlDocument, 'application/msword');
}

export const LegalNoticeGenerator: React.FC<LegalNoticeGeneratorProps> = ({
  draft,
  initialCaseDetails,
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

  useEffect(() => {
    if (initialCaseDetails) {
      setForm((current) => ({ ...current, caseDetails: initialCaseDetails }));
    }
  }, [initialCaseDetails]);

  useEffect(() => {
    if (!draft) {
      setForm(emptyInput);
      return;
    }
    setForm({
      clientDetails: draft.clientDetails,
      lawyerDetails: draft.lawyerDetails,
      recipientDetails: draft.recipientDetails,
      caseDetails: draft.caseDetails,
      relevantInfo: draft.relevantInfo,
    });
  }, [draft]);

  const canGenerate = useMemo(() => form.caseDetails.trim().length >= 5 && !isGenerating, [
    form.caseDetails,
    isGenerating,
  ]);

  const updateField = (field: keyof typeof emptyInput, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canGenerate) return;
    await onGenerate(form);
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
            New Notice
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <div className="mb-3 flex items-center gap-2 px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
            <Shield size={13} />
            Notice History
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
                No saved notices yet.
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
              <div className="section-kicker">LEGAL DRAFTING</div>
              <h1 className="mt-1 text-xl font-semibold text-on-surface">Legal Notice Generator</h1>
            </div>
          </div>
          {draft?.notice && (
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
                      downloadNoticeTxt(draft.notice);
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
                      downloadNoticeDoc(draft.notice);
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
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-[420px_1fr]">
          <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-outline-variant/40 bg-surface-container-low p-4">
            <div>
              <label className="field-label" htmlFor="clientDetails">
                Client name and details
              </label>
              <textarea
                id="clientDetails"
                className="text-field min-h-24 resize-y"
                value={form.clientDetails}
                onChange={(event) => updateField('clientDetails', event.target.value)}
                placeholder="Client name, address, phone/email, relationship to matter"
              />
            </div>

            <div>
              <label className="field-label" htmlFor="lawyerDetails">
                Lawyer information
              </label>
              <textarea
                id="lawyerDetails"
                className="text-field min-h-24 resize-y"
                value={form.lawyerDetails}
                onChange={(event) => updateField('lawyerDetails', event.target.value)}
                placeholder="Advocate name, office address, enrollment/contact details"
              />
            </div>

            <div>
              <label className="field-label" htmlFor="recipientDetails">
                Opposite party / recipient details
              </label>
              <textarea
                id="recipientDetails"
                className="text-field min-h-24 resize-y"
                value={form.recipientDetails}
                onChange={(event) => updateField('recipientDetails', event.target.value)}
                placeholder="Name, address, company, designation, known contact details"
              />
            </div>

            <div>
              <label className="field-label" htmlFor="caseDetails">
                Case details <span className="field-required">*</span>
              </label>
              <textarea
                id="caseDetails"
                className="text-field min-h-36 resize-y"
                value={form.caseDetails}
                onChange={(event) => updateField('caseDetails', event.target.value)}
                placeholder="Facts, dates, amounts, promises, breach, documents, and relief wanted"
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
                placeholder="Prior emails, notices, settlement talks, limitation concerns, documents"
              />
            </div>

            <button type="submit" className="primary-button w-full" disabled={!canGenerate}>
              {isGenerating ? <Loader2 className="animate-spin" size={18} /> : <Wand2 size={18} />}
              Generate Notice
            </button>

            {error && (
              <div className="rounded-lg border border-error/30 bg-error-container/40 p-3 text-sm text-on-error-container">
                {error}
              </div>
            )}
          </form>

          <div className="min-h-[520px] rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-5">
            {isGenerating ? (
              <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 text-on-surface-variant">
                <Loader2 className="animate-spin text-primary" size={30} />
                <div className="text-sm">Drafting legal notice...</div>
              </div>
            ) : draft?.notice ? (
              <div className="font-serif text-sm leading-relaxed text-on-surface" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {draft.notice}
              </div>
            ) : (
              <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center text-on-surface-variant">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText size={28} />
                </div>
                <h2 className="text-lg font-semibold text-on-surface">Your generated notice will appear here</h2>
                <p className="mt-2 max-w-md text-sm">
                  Enter the client, lawyer, recipient, case details, and supporting information to generate a formal Indian legal notice.
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
