import { FormEvent, useState, useRef } from 'react';
import { ArrowUp, Bot, FileSearch, Loader2, Paperclip, Plus, ShieldCheck, X } from 'lucide-react';
import { Matter, MatterOverview, uploadMatterDocument } from '../../core/api';

const commands = ['/research', '/draft', '/brief', '/review', '/next', '/timeline', '/diary'];

interface CaseAgentPanelProps {
  matter: Matter | null;
  overview: MatterOverview | null;
  onOpenContext: () => void;
  onRun: (command: string) => Promise<string>;
  onRefreshOverview?: () => void;
}

export function CaseAgentPanel({ matter, overview, onOpenContext, onRun, onRefreshOverview }: CaseAgentPanelProps) {
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const commandText = input.trim();
    if (!matter || (!commandText && !attachedFile) || isRunning || isUploading) return;

    setIsRunning(true);
    setError(null);

    try {
      if (attachedFile) {
        setIsUploading(true);
        try {
          await uploadMatterDocument(matter.matter_id, attachedFile);
          if (onRefreshOverview) {
            onRefreshOverview();
          }
        } catch (uploadErr) {
          setError(`Document upload failed: ${(uploadErr as Error).message}`);
          setIsUploading(false);
          setIsRunning(false);
          return;
        }
        setIsUploading(false);
      }

      let finalCommand = commandText;
      if (attachedFile && !commandText) {
        finalCommand = `/research Review and analyze the attached document: ${attachedFile.name}`;
      } else if (attachedFile && commandText && !commandText.startsWith('/')) {
        finalCommand = `${commandText} (Attached document: ${attachedFile.name})`;
      }

      setOutput(await onRun(finalCommand));
      setInput('');
      setAttachedFile(null);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'The Case Agent failed.');
    } finally {
      setIsRunning(false);
      setIsUploading(false);
    }
  };

  const contextCount = overview
    ? overview.documents.length + overview.open_tasks.length + overview.hearings.length
    : 0;

  return (
    <aside className="agent-panel">
      <header className="agent-header">
        <div className="agent-avatar"><Bot size={19} /></div>
        <div><strong>Case Agent</strong><span>Bounded to this matter</span></div>
        <span className="skeleton-tag">Connected</span>
      </header>

      <button type="button" className="context-card" onClick={onOpenContext}>
        <div className="context-title"><Paperclip size={15} /> Attached context</div>
        <p>{matter ? `${matter.title}: ${contextCount} linked context items.` : 'Select a matter to attach its context.'}</p>
      </button>

      <div className={output || error ? 'agent-result' : 'agent-empty'}>
        {!output && !error && (
          <>
            <div className="agent-empty-icon"><FileSearch size={25} /></div>
            <h2>Ask about this matter</h2>
            <p>Research, review, and prepare work from the selected matter’s permission-filtered evidence.</p>
          </>
        )}
        {output && <p>{output}</p>}
        {error && <p className="agent-error">{error}</p>}
      </div>

      <div className="command-list" aria-label="Case Agent commands">
        {commands.map((command) => (
          <button key={command} disabled={!matter || isRunning || isUploading} onClick={() => setInput(`${command} `)}>
            {command}
          </button>
        ))}
      </div>

      <form className="agent-composer" onSubmit={submit}>
        {attachedFile && (
          <div className="composer-attachment-chip">
            <Paperclip size={14} />
            <span className="attachment-name" title={attachedFile.name}>{attachedFile.name}</span>
            <span className="attachment-size">({(attachedFile.size / 1024).toFixed(0)} KB)</span>
            <button
              type="button"
              className="attachment-remove"
              onClick={() => setAttachedFile(null)}
              disabled={isRunning || isUploading}
              title="Remove attachment"
            >
              <X size={13} />
            </button>
          </div>
        )}

        <textarea
          disabled={!matter || isRunning || isUploading}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={matter ? 'Ask a question or enter /research, /next, /timeline…' : 'Create or select a matter first'}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit(e);
            }
          }}
        />

        <div className="composer-footer">
          <div className="composer-footer-left">
            <button
              type="button"
              className="attach-button"
              disabled={!matter || isRunning || isUploading}
              onClick={() => fileInputRef.current?.click()}
              title="Attach document (.pdf, .doc, .txt, image)"
            >
              <Plus size={18} />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
              onChange={(e) => {
                if (e.target.files?.[0]) setAttachedFile(e.target.files[0]);
              }}
            />
            <span><ShieldCheck size={14} /> Source verification required</span>
          </div>

          <button
            type="submit"
            className="send-button"
            disabled={!matter || (!input.trim() && !attachedFile) || isRunning || isUploading}
            aria-label="Send"
          >
            {isRunning || isUploading ? <Loader2 size={15} className="spin" /> : <ArrowUp size={17} />}
          </button>
        </div>
      </form>
    </aside>
  );
}

