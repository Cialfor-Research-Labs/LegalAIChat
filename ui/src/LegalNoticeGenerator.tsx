import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Download, FileText, Loader2, Wand2 } from 'lucide-react';
import { jsPDF } from 'jspdf';

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
  onGenerate: (input: Omit<LegalNoticeDraft, 'notice'>) => Promise<void>;
}

const emptyInput = {
  clientDetails: '',
  lawyerDetails: '',
  recipientDetails: '',
  caseDetails: '',
  relevantInfo: '',
};

function downloadNoticePdf(notice: string) {
  const pdf = new jsPDF({ unit: 'pt', format: 'a4' });
  const margin = 54;
  const maxWidth = 487;
  const lineHeight = 15;
  const pageHeight = pdf.internal.pageSize.getHeight();
  let y = margin;

  pdf.setFont('times', 'normal');
  pdf.setFontSize(11);

  notice.split('\n').forEach((paragraph) => {
    const lines = pdf.splitTextToSize(paragraph || ' ', maxWidth);
    lines.forEach((line: string) => {
      if (y > pageHeight - margin) {
        pdf.addPage();
        y = margin;
      }
      pdf.text(line, margin, y);
      y += lineHeight;
    });
    y += 4;
  });

  pdf.save('legal-notice.pdf');
}

export const LegalNoticeGenerator: React.FC<LegalNoticeGeneratorProps> = ({
  draft,
  initialCaseDetails,
  isGenerating = false,
  error,
  onGenerate,
}) => {
  const [form, setForm] = useState(emptyInput);

  useEffect(() => {
    if (initialCaseDetails) {
      setForm((current) => ({ ...current, caseDetails: initialCaseDetails }));
    }
  }, [initialCaseDetails]);

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
    <div className="flex h-full flex-col bg-surface">
      <div className="border-b border-outline-variant/20 bg-surface-container px-4 py-4 md:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <div>
            <div className="section-kicker">LEGAL DRAFTING</div>
            <h1 className="mt-1 text-xl font-semibold text-on-surface">Legal Notice Generator</h1>
          </div>
          {draft?.notice && (
            <button
              type="button"
              onClick={() => downloadNoticePdf(draft.notice)}
              className="primary-button"
            >
              <Download size={18} />
              Download PDF
            </button>
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
              <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-on-surface prose-p:leading-relaxed">
                <ReactMarkdown>{draft.notice}</ReactMarkdown>
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
  );
};
