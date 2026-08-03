import { FormEvent, useState, useRef } from 'react';
import { AlertCircle, CheckCircle2, Loader2, Upload } from 'lucide-react';
import { MatterCreateInput, parseMatterDocument } from '../../core/api';

interface CreateMatterDialogProps {
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onCreate: (input: MatterCreateInput, file?: File | null) => Promise<void>;
}

const ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt'];

export function CreateMatterDialog({ isSaving, error, onClose, onCreate }: CreateMatterDialogProps) {
  const [form, setForm] = useState<MatterCreateInput>({ title: '', description: '' });
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [autoFillFile, setAutoFillFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.title.trim()) return;
    await onCreate(form, autoFillFile);
  };

  const update = (field: keyof MatterCreateInput, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleFile = async (file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setParseError('Unsupported file format. Please upload a .pdf, .doc, or .txt file.');
      return;
    }

    setIsParsing(true);
    setParseError(null);
    setAutoFillFile(file);

    try {
      const fields = await parseMatterDocument(file);
      setForm((current) => ({
        ...current,
        title: fields.title || current.title,
        description: fields.description || current.description,
        case_number: fields.case_number ?? current.case_number ?? '',
        court: fields.court ?? current.court ?? '',
        jurisdiction: fields.jurisdiction ?? current.jurisdiction ?? '',
        stage: fields.stage ?? current.stage ?? '',
      }));
    } catch (err) {
      setParseError((err as Error).message || 'Could not parse document. You can still fill the fields manually.');
    } finally {
      setIsParsing(false);
    }
  };


  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && !isSaving && !isParsing && onClose()}
    >
      <form className="matter-dialog" onSubmit={submit}>
        <div>
          <div className="eyebrow">New matter</div>
          <h2>Create matter workspace</h2>
        </div>

        {error && <div className="workspace-error">{error}</div>}

        {/* Upload document to auto-fill details inside the modal */}
        <div className="matter-upload-section">
          <div
            className={`matter-dropzone ${isDragging ? 'dragging' : ''} ${isParsing ? 'parsing' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
            }}
            onClick={() => !isParsing && fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept=".pdf,.doc,.docx,.txt"
              onChange={(e) => {
                if (e.target.files?.[0]) handleFile(e.target.files[0]);
              }}
            />

            {isParsing ? (
              <div className="dropzone-status">
                <Loader2 size={20} className="spin" style={{ color: 'var(--green)' }} />
                <span>Reading document and extracting matter details…</span>
              </div>
            ) : autoFillFile ? (
              <div className="dropzone-status success">
                <CheckCircle2 size={20} style={{ color: '#059669' }} />
                <div>
                  <strong>Details auto-filled from {autoFillFile.name}</strong>
                  <span>This document will be saved into the matter workspace automatically</span>
                </div>
              </div>

            ) : (
              <div className="dropzone-status">
                <Upload size={20} style={{ color: '#059669' }} />
                <div>
                  <strong>Upload a document to auto-fill details</strong>
                  <span>Drag & drop or click to browse (.pdf, .doc, .txt)</span>
                </div>
              </div>
            )}
          </div>

          {parseError && (
            <div className="parse-error">
              <AlertCircle size={14} />
              <span>{parseError}</span>
            </div>
          )}

          <div className="or-divider">
            <span>OR FILL MANUALLY</span>
          </div>
        </div>

        <label>
          Title
          <input
            autoFocus
            required
            maxLength={300}
            value={form.title}
            onChange={(e) => update('title', e.target.value)}
            placeholder="e.g. Contract Breach Dispute or Party v. Party"
          />
        </label>
        <label>
          Description
          <textarea
            maxLength={10000}
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
            placeholder="Brief overview of case facts, claims, or document summary"
          />
        </label>
        <div className="dialog-grid">
          <label>
            Case number
            <input
              maxLength={200}
              value={form.case_number || ''}
              onChange={(e) => update('case_number', e.target.value)}
              placeholder="e.g. OS 1042/2024 or FIR 88/2023"
            />
          </label>
          <label>
            Court
            <input
              maxLength={300}
              value={form.court || ''}
              onChange={(e) => update('court', e.target.value)}
              placeholder="e.g. Telangana High Court"
            />
          </label>
          <label>
            Jurisdiction
            <input
              maxLength={300}
              value={form.jurisdiction || ''}
              onChange={(e) => update('jurisdiction', e.target.value)}
              placeholder="e.g. Hyderabad, Telangana"
            />
          </label>
          <label>
            Stage
            <input
              maxLength={200}
              value={form.stage || ''}
              onChange={(e) => update('stage', e.target.value)}
              placeholder="e.g. Initial / Evidence / Hearing"
            />
          </label>
        </div>
        <div className="dialog-actions">
          <button type="button" onClick={onClose} disabled={isSaving || isParsing}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={isSaving || isParsing || !form.title.trim()}>
            {isSaving ? 'Creating…' : 'Create matter'}
          </button>
        </div>
      </form>
    </div>
  );
}

