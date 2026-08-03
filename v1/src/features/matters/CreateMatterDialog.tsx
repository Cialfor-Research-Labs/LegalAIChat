import { FormEvent, useState } from 'react';
import { MatterCreateInput } from '../../core/api';

interface CreateMatterDialogProps {
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onCreate: (input: MatterCreateInput) => Promise<void>;
}

export function CreateMatterDialog({ isSaving, error, onClose, onCreate }: CreateMatterDialogProps) {
  const [form, setForm] = useState<MatterCreateInput>({ title: '', description: '' });

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.title.trim()) return;
    await onCreate(form);
  };

  const update = (field: keyof MatterCreateInput, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form className="matter-dialog" onSubmit={submit}>
        <div><div className="eyebrow">New matter</div><h2>Create matter workspace</h2></div>
        {error && <div className="workspace-error">{error}</div>}
        <label>Title<input autoFocus required maxLength={300} value={form.title} onChange={(e) => update('title', e.target.value)} /></label>
        <label>Description<textarea maxLength={10000} value={form.description} onChange={(e) => update('description', e.target.value)} /></label>
        <div className="dialog-grid">
          <label>Case number<input maxLength={200} value={form.case_number || ''} onChange={(e) => update('case_number', e.target.value)} /></label>
          <label>Court<input maxLength={300} value={form.court || ''} onChange={(e) => update('court', e.target.value)} /></label>
          <label>Jurisdiction<input maxLength={300} value={form.jurisdiction || ''} onChange={(e) => update('jurisdiction', e.target.value)} /></label>
          <label>Stage<input maxLength={200} value={form.stage || ''} onChange={(e) => update('stage', e.target.value)} /></label>
        </div>
        <div className="dialog-actions">
          <button type="button" onClick={onClose} disabled={isSaving}>Cancel</button>
          <button type="submit" className="primary" disabled={isSaving || !form.title.trim()}>{isSaving ? 'Creating…' : 'Create matter'}</button>
        </div>
      </form>
    </div>
  );
}
