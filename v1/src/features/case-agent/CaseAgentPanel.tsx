import { FormEvent, useState } from 'react';
import { ArrowUp, Bot, FileSearch, Paperclip, ShieldCheck } from 'lucide-react';
import { Matter, MatterOverview } from '../../core/api';

const commands = ['/research', '/draft', '/brief', '/review', '/next', '/timeline', '/diary'];

interface CaseAgentPanelProps {
  matter: Matter | null;
  overview: MatterOverview | null;
  onRun: (command: string) => Promise<string>;
}

export function CaseAgentPanel({ matter, overview, onRun }: CaseAgentPanelProps) {
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const command = input.trim();
    if (!matter || !command || isRunning) return;
    setIsRunning(true);
    setError(null);
    try {
      setOutput(await onRun(command));
      setInput('');
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'The Case Agent failed.');
    } finally {
      setIsRunning(false);
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

      <div className="context-card">
        <div className="context-title"><Paperclip size={15} /> Attached context</div>
        <p>{matter ? `${matter.title}: ${contextCount} linked context items.` : 'Select a matter to attach its context.'}</p>
      </div>

      <div className={output || error ? 'agent-result' : 'agent-empty'}>
        {!output && !error && <>
          <div className="agent-empty-icon"><FileSearch size={25} /></div>
          <h2>Ask about this matter</h2>
          <p>Research, review, and prepare work from the selected matter’s permission-filtered evidence.</p>
        </>}
        {output && <p>{output}</p>}
        {error && <p className="agent-error">{error}</p>}
      </div>

      <div className="command-list" aria-label="Case Agent commands">
        {commands.map((command) => (
          <button key={command} disabled={!matter || isRunning} onClick={() => setInput(`${command} `)}>{command}</button>
        ))}
      </div>

      <form className="agent-composer" onSubmit={submit}>
        <textarea
          disabled={!matter || isRunning}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={matter ? 'Ask a question or enter /research, /next, /timeline…' : 'Create or select a matter first'}
        />
        <div className="composer-footer">
          <span><ShieldCheck size={14} /> Source verification required</span>
          <button disabled={!matter || !input.trim() || isRunning} aria-label="Send"><ArrowUp size={17} /></button>
        </div>
      </form>
    </aside>
  );
}
