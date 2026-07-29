import { ArrowUp, Bot, FileSearch, Paperclip, ShieldCheck } from 'lucide-react';

const commands = ['/research', '/draft', '/brief', '/review', '/next', '/timeline', '/diary'];

export function CaseAgentPanel() {
  return (
    <aside className="agent-panel">
      <header className="agent-header">
        <div className="agent-avatar"><Bot size={19} /></div>
        <div>
          <strong>Case Agent</strong>
          <span>Bounded to this matter</span>
        </div>
        <span className="skeleton-tag">Skeleton</span>
      </header>

      <div className="context-card">
        <div className="context-title"><Paperclip size={15} /> Attached context</div>
        <p>No matter, files, hearing, tasks, or orders attached.</p>
      </div>

      <div className="agent-empty">
        <div className="agent-empty-icon"><FileSearch size={25} /></div>
        <h2>Ask about this matter</h2>
        <p>The future agent will research, draft, review, and prepare hearing work from permission-filtered evidence.</p>
      </div>

      <div className="command-list" aria-label="Planned Case Agent commands">
        {commands.map((command) => <span key={command}>{command}</span>)}
      </div>

      <div className="agent-composer">
        <textarea disabled placeholder="Connect a matter before using the Case Agent" />
        <div className="composer-footer">
          <span><ShieldCheck size={14} /> Source verification required</span>
          <button disabled aria-label="Send"><ArrowUp size={17} /></button>
        </div>
      </div>
    </aside>
  );
}
